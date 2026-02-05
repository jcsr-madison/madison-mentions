"""Reporter dossier API endpoint."""

import re
from datetime import date
from fastapi import APIRouter, HTTPException

from ..models.schemas import Article, ReporterDossier
from ..services.perigon import fetch_reporter_articles as fetch_perigon_articles
from ..services.newsapi import fetch_reporter_articles as fetch_newsapi_articles
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


def deduplicate_by_url(articles: list) -> list:
    """Remove duplicate articles based on URL."""
    seen = set()
    unique = []
    for article in articles:
        url = article.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(article)
    return unique


@router.get("/reporter/{name}", response_model=ReporterDossier)
async def get_reporter_dossier(name: str):
    """Get a comprehensive dossier for a reporter.

    Fetches recent articles, summarizes headlines, analyzes outlet history,
    and detects potential outlet changes.

    Uses Perigon as primary source (230K+ journalists), falls back to
    NewsAPI.ai for additional coverage.
    """
    # Validate input
    name = name.strip()
    if not name or len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Reporter name must be at least 2 characters"
        )

    # Fetch articles from Perigon (primary - best journalist coverage)
    articles = await fetch_perigon_articles(name)

    # Dedupe syndicated content (same headline across multiple outlets)
    articles = deduplicate_by_headline(articles)

    # If Perigon returns few results, supplement with NewsAPI.ai
    if len(articles) < 5:
        newsapi_articles = await fetch_newsapi_articles(name)
        if newsapi_articles:
            articles.extend(newsapi_articles)
            articles = deduplicate_by_url(articles)
            articles = deduplicate_by_headline(articles)

    if not articles:
        # Return empty dossier instead of error
        return ReporterDossier(
            reporter_name=name,
            query_date=date.today(),
            articles=[],
            outlet_history=[],
            outlet_change_detected=False,
            outlet_change_note=None
        )

    # Add summaries to articles
    articles = await summarize_headlines(articles)

    # Analyze outlet history
    outlet_history = get_outlet_history(articles)

    # Detect outlet changes
    change_detected, change_note = detect_outlet_change(articles)

    # Convert to Article models
    article_models = [
        Article(
            headline=a["headline"],
            outlet=a["outlet"],
            date=a["date"] if isinstance(a["date"], date) else date.fromisoformat(a["date"]),
            url=a["url"],
            summary=a.get("summary")
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
        outlet_change_detected=change_detected,
        outlet_change_note=change_note
    )
