"""NewsAPI.ai (Event Registry) client for fetching reporter bylines."""

import os
from datetime import datetime
from typing import List, Optional

import httpx
from dotenv import load_dotenv

from ..db.cache import get_cached_query, set_cached_query


load_dotenv()

NEWSAPI_BASE_URL = "https://eventregistry.org/api/v1"
REQUEST_TIMEOUT = 30.0


def get_api_key() -> str:
    """Get NewsAPI.ai API key from environment."""
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        raise ValueError("NEWSAPI_API_KEY environment variable not set")
    return api_key


async def get_author_uri(client: httpx.AsyncClient, author_name: str) -> Optional[str]:
    """Get the author URI for a given author name using suggest endpoint."""
    api_key = get_api_key()

    response = await client.post(
        f"{NEWSAPI_BASE_URL}/suggestAuthors",
        json={
            "prefix": author_name,
            "apiKey": api_key
        },
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    data = response.json()

    # Return the best matching author URI
    if data and len(data) > 0:
        return data[0].get("uri")
    return None


def parse_article_response(data: dict) -> List[dict]:
    """Parse NewsAPI.ai article response into standardized article list."""
    articles = []

    if not data or "articles" not in data:
        return articles

    results = data.get("articles", {}).get("results", [])

    for item in results:
        try:
            # Parse the date
            date_str = item.get("date", "")
            if date_str:
                article_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                continue

            # Get source info
            source = item.get("source", {})
            outlet = source.get("title", source.get("uri", "Unknown"))

            # Clean up outlet name
            outlet = outlet.replace("www.", "").replace(".com", "").replace(".org", "")
            if not outlet[0].isupper():
                outlet = outlet.title()

            article = {
                "headline": item.get("title", "Untitled"),
                "outlet": outlet,
                "date": article_date.isoformat(),
                "url": item.get("url", ""),
            }

            if article["url"]:
                articles.append(article)

        except (ValueError, KeyError):
            continue

    return articles


async def fetch_reporter_articles(reporter_name: str) -> List[dict]:
    """Fetch articles by reporter from NewsAPI.ai, with caching."""
    # Check cache first
    cached = get_cached_query(reporter_name)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            api_key = get_api_key()

            # First, get the author URI
            author_uri = await get_author_uri(client, reporter_name)

            if not author_uri:
                # No author found - try keyword search as fallback
                response = await client.post(
                    f"{NEWSAPI_BASE_URL}/article/getArticles",
                    json={
                        "keyword": reporter_name,
                        "keywordOper": "and",
                        "lang": "eng",
                        "articlesCount": 100,
                        "articlesSortBy": "date",
                        "articlesSortByAsc": False,
                        "includeArticleSocialScore": False,
                        "apiKey": api_key
                    },
                    timeout=REQUEST_TIMEOUT
                )
            else:
                # Query articles by author URI
                response = await client.post(
                    f"{NEWSAPI_BASE_URL}/article/getArticles",
                    json={
                        "authorUri": author_uri,
                        "lang": "eng",
                        "articlesCount": 100,
                        "articlesSortBy": "date",
                        "articlesSortByAsc": False,
                        "includeArticleSocialScore": False,
                        "apiKey": api_key
                    },
                    timeout=REQUEST_TIMEOUT
                )

            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - return empty but don't cache
                return []
            raise
        except (httpx.RequestError, ValueError):
            # Network error or invalid JSON - return empty
            return []

    articles = parse_article_response(data)

    # Cache the results
    set_cached_query(reporter_name, articles)

    return articles
