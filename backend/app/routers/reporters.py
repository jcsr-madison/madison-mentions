"""Reporter dossier API endpoint."""

import re
from collections import Counter
from datetime import date
from typing import List

from fastapi import APIRouter, HTTPException

from ..models.schemas import (
    Article, BeatCount, ReporterDossier, SocialLinks,
    JournalistSummary, JournalistSearchResponse
)
from ..services.perigon import (
    fetch_reporter_articles as fetch_perigon_articles,
    search_journalists_by_topic
)
from ..services.summarizer import summarize_headlines
from ..services.analyzer import get_outlet_history, detect_outlet_change


router = APIRouter(prefix="/api", tags=["reporters"])

# Outlet priority for deduplication (higher = preferred)
OUTLET_PRIORITY = {
    "New York Times": 100,
    "Wall Street Journal": 100,
    "Washington Post": 100,
    "Bloomberg": 95,
    "Reuters": 95,
    "AP News": 95,
    "Politico": 90,
    "The Atlantic": 90,
    "Axios": 85,
    "CNN": 80,
    "NBC News": 80,
    "CBS News": 80,
    "ABC News": 80,
    "NPR": 80,
    "Los Angeles Times": 75,
    "Chicago Tribune": 75,
    "Boston Globe": 75,
    "Seattle Times": 70,
    "Miami Herald": 70,
    "SF Chronicle": 70,
}


def normalize_headline(headline: str) -> str:
    """Normalize headline for comparison."""
    # Lowercase
    h = headline.lower()
    # Remove punctuation and extra whitespace
    h = re.sub(r'[^\w\s]', '', h)
    h = re.sub(r'\s+', ' ', h).strip()
    # Remove common prefixes like "Live Updates:"
    h = re.sub(r'^(live updates?|breaking|update)\s*:?\s*', '', h)
    return h


def deduplicate_by_headline(articles: list) -> list:
    """Remove duplicate syndicated articles, keeping the primary outlet version.

    Many articles are syndicated across McClatchy papers and other networks.
    This keeps only one version, preferring major outlets over regional ones.
    """
    # Group by normalized headline
    headline_groups = {}
    for article in articles:
        key = normalize_headline(article.get("headline", ""))
        if not key:
            continue
        if key not in headline_groups:
            headline_groups[key] = []
        headline_groups[key].append(article)

    # For each group, keep the article from the highest-priority outlet
    unique = []
    for key, group in headline_groups.items():
        if len(group) == 1:
            unique.append(group[0])
        else:
            # Sort by outlet priority (highest first), then by date (newest first)
            group.sort(
                key=lambda a: (
                    OUTLET_PRIORITY.get(a.get("outlet", ""), 0),
                    a.get("date", "")
                ),
                reverse=True
            )
            unique.append(group[0])

    # Sort by date descending
    unique.sort(key=lambda a: a.get("date", ""), reverse=True)
    return unique


def get_primary_beats(articles: list) -> List[BeatCount]:
    """Calculate primary beats/topics from all articles."""
    topic_counts = Counter()

    for article in articles:
        topics = article.get("topics", [])
        for topic in topics:
            topic_counts[topic] += 1

    # Return top beats sorted by count
    return [
        BeatCount(beat=topic, count=count)
        for topic, count in topic_counts.most_common(10)
    ]


@router.get("/reporter/{name}", response_model=ReporterDossier)
async def get_reporter_dossier(name: str):
    """Get a comprehensive dossier for a reporter.

    Fetches recent articles, summarizes headlines, analyzes outlet history,
    and detects potential outlet changes.

    Data source: Perigon (230K+ journalists with social profiles).
    """
    # Validate input
    name = name.strip()
    if not name or len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Reporter name must be at least 2 characters"
        )

    # Fetch articles from Perigon
    articles, social_links_data = await fetch_perigon_articles(name)

    # Dedupe syndicated content (same headline across multiple outlets)
    articles = deduplicate_by_headline(articles)

    # Build social links model
    social_links = None
    if social_links_data:
        social_links = SocialLinks(
            twitter_handle=social_links_data.get("twitter_handle"),
            twitter_url=social_links_data.get("twitter_url"),
            linkedin_url=social_links_data.get("linkedin_url"),
            website_url=social_links_data.get("website_url"),
            title=social_links_data.get("title"),
        )

    if not articles:
        # Return empty dossier instead of error
        return ReporterDossier(
            reporter_name=name,
            query_date=date.today(),
            articles=[],
            outlet_history=[],
            primary_beats=[],
            social_links=social_links,
            outlet_change_detected=False,
            outlet_change_note=None
        )

    # Add summaries to articles
    articles = await summarize_headlines(articles)

    # Analyze outlet history
    outlet_history = get_outlet_history(articles)

    # Calculate primary beats from topics
    primary_beats = get_primary_beats(articles)

    # Detect outlet changes
    change_detected, change_note = detect_outlet_change(articles)

    # Convert to Article models
    article_models = [
        Article(
            headline=a["headline"],
            outlet=a["outlet"],
            date=a["date"] if isinstance(a["date"], date) else date.fromisoformat(a["date"]),
            url=a["url"],
            summary=a.get("summary"),
            topics=a.get("topics", [])
        )
        for a in articles
    ]

    # Sort by date descending
    article_models.sort(key=lambda a: a.date, reverse=True)

    return ReporterDossier(
        reporter_name=name,
        query_date=date.today(),
        articles=article_models,
        outlet_history=outlet_history,
        primary_beats=primary_beats,
        social_links=social_links,
        outlet_change_detected=change_detected,
        outlet_change_note=change_note
    )


@router.get("/journalists/search", response_model=JournalistSearchResponse)
async def search_journalists(topic: str, limit: int = 20):
    """Search for journalists covering a specific topic/beat.

    Find reporters who cover a particular beat like Politics, Technology,
    Finance, etc. Returns journalists with their outlets and social links.

    Args:
        topic: The topic/beat to search for (e.g., "Politics", "Technology")
        limit: Maximum number of results (default 20, max 50)
    """
    # Validate input
    topic = topic.strip()
    if not topic or len(topic) < 2:
        raise HTTPException(
            status_code=400,
            detail="Topic must be at least 2 characters"
        )

    # Validate and cap limit (1-50)
    if limit < 1:
        limit = 20
    limit = min(limit, 50)

    # Search journalists by topic
    journalists_data = await search_journalists_by_topic(topic, size=limit)

    # Convert to models
    journalists = [
        JournalistSummary(
            name=j["name"],
            title=j.get("title"),
            outlets=j.get("outlets", []),
            twitter_handle=j.get("twitter_handle"),
            twitter_url=j.get("twitter_url"),
            linkedin_url=j.get("linkedin_url"),
            article_count=j.get("article_count", 0),
        )
        for j in journalists_data
    ]

    return JournalistSearchResponse(
        topic=topic,
        query_date=date.today(),
        total_results=len(journalists),
        journalists=journalists
    )
