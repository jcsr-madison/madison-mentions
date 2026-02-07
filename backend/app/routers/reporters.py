"""Reporter dossier API endpoint with cache-first architecture."""

import json
import re
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..db.reporter_store import (
    get_reporter,
    is_reporter_fresh,
    get_reporter_articles,
    get_latest_article_date,
    upsert_reporter,
    insert_articles,
    update_reporter_profile,
    update_relevance,
    get_relevance,
)
from ..models.schemas import Article, ReporterDossier, SocialLinks
from ..services.perigon import search_and_get_journalist, fetch_articles_since
from ..services.summarizer import summarize_headlines, generate_reporter_profile
from ..services.analyzer import detect_outlet_change
from ..services.relevance_classifier import classify_reporter


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
    h = headline.lower()
    h = re.sub(r'[^\w\s]', '', h)
    h = re.sub(r'\s+', ' ', h).strip()
    h = re.sub(r'^(live updates?|breaking|update)\s*:?\s*', '', h)
    return h


def deduplicate_by_headline(articles: list) -> list:
    """Remove duplicate syndicated articles, keeping the primary outlet version."""
    headline_groups = {}
    for article in articles:
        key = normalize_headline(article.get("headline", ""))
        if not key:
            continue
        if key not in headline_groups:
            headline_groups[key] = []
        headline_groups[key].append(article)

    unique = []
    for key, group in headline_groups.items():
        if len(group) == 1:
            unique.append(group[0])
        else:
            group.sort(
                key=lambda a: (
                    OUTLET_PRIORITY.get(a.get("outlet", ""), 0),
                    a.get("date", "")
                ),
                reverse=True
            )
            unique.append(group[0])

    unique.sort(key=lambda a: a.get("date", ""), reverse=True)
    return unique


def build_dossier_from_db(reporter: dict) -> ReporterDossier:
    """Build a ReporterDossier from a stored reporter record and its articles."""
    reporter_id = reporter["id"]
    db_articles = get_reporter_articles(reporter_id)

    # Convert DB rows to dicts suitable for detect_outlet_change
    articles_for_analysis = [
        {
            "headline": a["headline"],
            "outlet": a["outlet"],
            "date": a["date"],
            "url": a["url"],
            "summary": a.get("summary"),
            "topics": a.get("topics", []),
        }
        for a in db_articles
    ]

    # Parse social links
    social_links = None
    social_links_json = reporter.get("social_links_json")
    if social_links_json:
        try:
            sl = json.loads(social_links_json)
            social_links = SocialLinks(
                twitter_handle=sl.get("twitter_handle"),
                twitter_url=sl.get("twitter_url"),
                linkedin_url=sl.get("linkedin_url"),
                website_url=sl.get("website_url"),
                title=sl.get("title"),
            )
        except (json.JSONDecodeError, TypeError):
            pass

    # Detect outlet changes
    change_detected, change_note = detect_outlet_change(articles_for_analysis)

    # Parse last_updated
    last_updated = None
    if reporter.get("last_updated"):
        try:
            last_updated = datetime.fromisoformat(reporter["last_updated"])
        except (ValueError, TypeError):
            pass

    # Build article models (skip articles with missing dates)
    article_models = []
    for a in articles_for_analysis:
        article_date = a.get("date")
        if not article_date:
            continue
        if not isinstance(article_date, date):
            try:
                article_date = date.fromisoformat(article_date)
            except (ValueError, TypeError):
                continue
        article_models.append(Article(
            headline=a["headline"],
            outlet=a["outlet"],
            date=article_date,
            url=a["url"],
            summary=a.get("summary"),
            topics=a.get("topics", []),
        ))
    article_models.sort(key=lambda a: a.date, reverse=True)

    return ReporterDossier(
        reporter_name=reporter["name"].title(),
        query_date=date.today(),
        articles=article_models,
        current_outlet=reporter.get("current_outlet"),
        reporter_bio=reporter.get("reporter_bio"),
        social_links=social_links,
        outlet_change_detected=change_detected,
        outlet_change_note=change_note,
        last_updated=last_updated,
        pro_services_relevant=reporter.get("pro_services_relevant"),
        relevance_rationale=reporter.get("relevance_rationale"),
    )


def _classify_if_needed(reporter_id: int, reporter_name: str, articles: list) -> None:
    """Run relevance classification if not already done."""
    existing = get_relevance(reporter_id)
    if existing is not None:
        return  # Already classified — never re-evaluate

    if not articles:
        return  # No articles to classify on

    outlets = set(a.get("outlet", "") for a in articles if a.get("outlet"))
    summaries = [
        a.get("summary") or a.get("headline", "")
        for a in articles
    ]
    relevant, rationale = classify_reporter(reporter_name, outlets, summaries)
    update_relevance(reporter_id, relevant, rationale)


@router.get("/reporter/{name}", response_model=ReporterDossier)
async def get_reporter_dossier(name: str, refresh: bool = False):
    """Get a comprehensive dossier for a reporter.

    3-tier cache-first architecture:
    - Tier 2: Fresh DB hit — returns instantly, no API calls
    - Tier 3: Stale or forced refresh — incremental update from Perigon
    - Tier 1: Cold start — full fetch from Perigon, stores everything
    """
    name = name.strip()
    if not name or len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Reporter name must be at least 2 characters"
        )

    reporter = get_reporter(name)

    # --- Tier 2: Fresh DB hit ---
    if reporter and is_reporter_fresh(reporter) and not refresh:
        db_articles = get_reporter_articles(reporter["id"])
        if db_articles:
            # Classify if not yet evaluated
            if reporter.get("pro_services_relevant") is None:
                articles_for_classify = [
                    {"outlet": a["outlet"], "summary": a.get("summary"), "headline": a["headline"]}
                    for a in db_articles
                ]
                _classify_if_needed(reporter["id"], name, articles_for_classify)
                reporter = get_reporter(name)  # Re-fetch with classification
            return build_dossier_from_db(reporter)

    # --- Tier 3: Stale or forced refresh (incremental) ---
    if reporter and reporter.get("perigon_journalist_id"):
        journalist_id = reporter["perigon_journalist_id"]
        reporter_id = reporter["id"]

        # Determine incremental fetch boundary
        latest_date = get_latest_article_date(reporter_id)
        since_date = None
        if latest_date:
            next_day = (date.fromisoformat(latest_date) + timedelta(days=1)).isoformat()
            since_date = next_day

        # Fetch only new articles from Perigon
        new_articles = await fetch_articles_since(journalist_id, since_date)
        new_articles = deduplicate_by_headline(new_articles)

        if new_articles:
            # Summarize only the new articles
            new_articles = await summarize_headlines(new_articles)
            insert_articles(reporter_id, new_articles)

        # Regenerate profile with ALL articles (old + new)
        all_db_articles = get_reporter_articles(reporter_id)
        all_articles_dicts = [
            {
                "headline": a["headline"],
                "outlet": a["outlet"],
                "date": a["date"],
                "url": a["url"],
                "summary": a.get("summary"),
                "topics": a.get("topics", []),
            }
            for a in all_db_articles
        ]

        # Get social title for profile generation
        social_title = None
        if reporter.get("social_links_json"):
            try:
                sl = json.loads(reporter["social_links_json"])
                social_title = sl.get("title")
            except (json.JSONDecodeError, TypeError):
                pass

        current_outlet, reporter_bio = generate_reporter_profile(
            name, all_articles_dicts, social_title
        )
        update_reporter_profile(reporter_id, current_outlet, reporter_bio)

        # Classify if not yet evaluated
        if reporter.get("pro_services_relevant") is None:
            _classify_if_needed(reporter_id, name, all_articles_dicts)

        # Re-fetch the updated reporter record
        reporter = get_reporter(name)
        return build_dossier_from_db(reporter)

    # --- Tier 1: Cold start (no record) ---
    journalist_data = await search_and_get_journalist(name)

    social_links_data = journalist_data.get("social_links") if journalist_data else None
    social_links = None
    if social_links_data:
        social_links = SocialLinks(
            twitter_handle=social_links_data.get("twitter_handle"),
            twitter_url=social_links_data.get("twitter_url"),
            linkedin_url=social_links_data.get("linkedin_url"),
            website_url=social_links_data.get("website_url"),
            title=social_links_data.get("title"),
        )

    if not journalist_data:
        return ReporterDossier(
            reporter_name=name,
            query_date=date.today(),
            articles=[],
            social_links=social_links,
            outlet_change_detected=False,
            outlet_change_note=None,
        )

    journalist_id = journalist_data["id"]

    # Full 365-day fetch
    articles = await fetch_articles_since(journalist_id)
    articles = deduplicate_by_headline(articles)

    if not articles:
        upsert_reporter(
            name=name,
            perigon_id=journalist_id,
            social_links=social_links_data,
            source="perigon",
        )
        return ReporterDossier(
            reporter_name=name,
            query_date=date.today(),
            articles=[],
            social_links=social_links,
            outlet_change_detected=False,
            outlet_change_note=None,
        )

    # Summarize all articles
    articles = await summarize_headlines(articles)

    # Generate profile
    social_title = social_links_data.get("title") if social_links_data else None
    current_outlet, reporter_bio = generate_reporter_profile(name, articles, social_title)

    # Store reporter and articles
    reporter_id = upsert_reporter(
        name=name,
        perigon_id=journalist_id,
        social_links=social_links_data,
        current_outlet=current_outlet,
        bio=reporter_bio,
        source="perigon",
    )
    insert_articles(reporter_id, articles)

    # Classify relevance for new reporters
    _classify_if_needed(reporter_id, name, articles)

    # Return from DB for consistency
    reporter = get_reporter(name)
    return build_dossier_from_db(reporter)
