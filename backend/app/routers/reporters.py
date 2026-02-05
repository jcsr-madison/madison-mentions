"""Reporter dossier API endpoint."""

from datetime import date
from fastapi import APIRouter, HTTPException

from ..models.schemas import Article, ReporterDossier
from ..services.newsapi import fetch_reporter_articles
from ..services.summarizer import summarize_headlines
from ..services.analyzer import get_outlet_history, detect_outlet_change


router = APIRouter(prefix="/api", tags=["reporters"])


@router.get("/reporter/{name}", response_model=ReporterDossier)
async def get_reporter_dossier(name: str):
    """Get a comprehensive dossier for a reporter.

    Fetches recent articles, summarizes headlines, analyzes outlet history,
    and detects potential outlet changes.
    """
    # Validate input
    name = name.strip()
    if not name or len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Reporter name must be at least 2 characters"
        )

    # Fetch articles from NewsAPI.ai
    articles = await fetch_reporter_articles(name)

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
