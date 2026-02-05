"""NewsAPI.ai (Event Registry) client for fetching reporter bylines.

Note: NewsAPI.ai free tier has limited coverage. Author metadata is inconsistent
across sources. This implementation tries multiple search strategies to maximize
results.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple

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


async def get_author_uris(client: httpx.AsyncClient, author_name: str, api_key: str) -> List[str]:
    """Get all author URIs for a given author name."""
    try:
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

        # Return all matching URIs (not just the first one)
        return [item.get("uri") for item in data if item.get("uri")]
    except Exception:
        return []


async def search_by_author_uris(
    client: httpx.AsyncClient,
    author_uris: List[str],
    api_key: str
) -> List[dict]:
    """Search for articles by multiple author URIs."""
    if not author_uris:
        return []

    # Build OR query for all author URIs
    try:
        response = await client.post(
            f"{NEWSAPI_BASE_URL}/article/getArticles",
            json={
                "query": {
                    "$query": {
                        "$or": [{"authorUri": uri} for uri in author_uris[:10]]  # Limit to 10 URIs
                    }
                },
                "resultType": "articles",
                "articlesSortBy": "date",
                "articlesSortByAsc": False,
                "articlesCount": 100,
                "includeArticleAuthors": True,
                "apiKey": api_key
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("articles", {}).get("results", [])
    except Exception:
        return []


async def search_by_keyword(
    client: httpx.AsyncClient,
    author_name: str,
    api_key: str
) -> List[dict]:
    """Search for articles by author name as keyword.

    Only uses keyword search as a last resort, with strict filtering
    to only include articles where the person is actually an author.
    """
    articles = []
    name_parts = author_name.strip().split()

    if len(name_parts) < 2:
        return []

    # Search for articles that have the author name in the authors metadata
    # This is more reliable than body/headline search
    try:
        response = await client.post(
            f"{NEWSAPI_BASE_URL}/article/getArticles",
            json={
                "keyword": f'"{author_name}"',
                "lang": "eng",
                "articlesCount": 100,
                "articlesSortBy": "date",
                "articlesSortByAsc": False,
                "includeArticleAuthors": True,
                "apiKey": api_key
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        # STRICT filter: only include if author name appears in the authors list
        name_lower = author_name.lower()
        for article in data.get("articles", {}).get("results", []):
            author_list = article.get("authors", [])
            author_names = [a.get("name", "").lower() for a in author_list]
            combined = " ".join(author_names)

            # Check if our author is actually in the byline
            if name_lower in combined:
                articles.append(article)
                continue

            # Also check partial name match (first + last name separately)
            name_parts_lower = [p.lower() for p in name_parts]
            if len(name_parts_lower) >= 2:
                first_name = name_parts_lower[0]
                last_name = name_parts_lower[-1]
                for author_name_str in author_names:
                    if first_name in author_name_str and last_name in author_name_str:
                        articles.append(article)
                        break
    except Exception:
        pass

    return articles


def deduplicate_articles(articles: List[dict]) -> List[dict]:
    """Remove duplicate articles based on URL."""
    seen_urls: Set[str] = set()
    unique = []

    for article in articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)

    return unique


def parse_article(item: dict) -> Optional[dict]:
    """Parse a single article from the API response."""
    try:
        # Parse the date
        date_str = item.get("date", "")
        if not date_str:
            return None

        article_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Get source info
        source = item.get("source", {})
        outlet = source.get("title", source.get("uri", "Unknown"))

        # Clean up outlet name
        if outlet:
            outlet = outlet.replace("www.", "")
            # Remove common TLDs for cleaner display
            for tld in [".com", ".org", ".net", ".co.uk", ".io"]:
                outlet = outlet.replace(tld, "")
            if outlet and not outlet[0].isupper():
                outlet = outlet.title()

        url = item.get("url", "")
        if not url:
            return None

        # Extract author names for metadata
        authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]

        return {
            "headline": item.get("title", "Untitled"),
            "outlet": outlet or "Unknown",
            "date": article_date.isoformat(),
            "url": url,
            "authors": authors,  # Include for filtering/display
        }
    except (ValueError, KeyError, AttributeError):
        return None


def parse_articles(items: List[dict]) -> List[dict]:
    """Parse multiple articles from API response."""
    articles = []
    for item in items:
        parsed = parse_article(item)
        if parsed:
            articles.append(parsed)
    return articles


def filter_by_author_name(articles: List[dict], author_name: str) -> List[dict]:
    """Filter articles to those written BY the author.

    Strict filtering: only keep articles where the reporter is in the author metadata.
    Articles that just mention the reporter's name are filtered out.
    """
    name_lower = author_name.lower()
    name_parts = name_lower.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if name_parts else ""

    filtered = []
    for article in articles:
        author_list = article.get("authors", [])

        # If article has author metadata, check if our reporter is listed
        if author_list:
            author_names_lower = [a.lower() for a in author_list]
            combined = " ".join(author_names_lower)

            # Match full name or first+last name
            is_author = (
                name_lower in combined or
                (first_name and last_name and first_name in combined and last_name in combined)
            )

            if is_author:
                filtered.append(article)
        # If no author metadata, check headline - skip if name is in headline (article ABOUT them)
        else:
            headline_lower = article.get("headline", "").lower()
            if name_lower not in headline_lower and last_name not in headline_lower:
                # No author data and name not in headline - might be BY them
                # But this is unreliable, so we skip it to avoid false positives
                pass

    # Remove the 'authors' field before returning
    for article in filtered:
        article.pop("authors", None)

    return filtered


async def fetch_reporter_articles(reporter_name: str) -> List[dict]:
    """Fetch articles by reporter from NewsAPI.ai, with caching.

    Uses multiple search strategies:
    1. Search by author URI (if the author is in the system)
    2. Search by keyword patterns
    3. Deduplicate and filter results
    """
    # Check cache first
    cached = get_cached_query(reporter_name)
    if cached is not None:
        return cached

    all_articles: List[dict] = []

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            api_key = get_api_key()

            # Strategy 1: Get all author URIs and search
            author_uris = await get_author_uris(client, reporter_name, api_key)
            if author_uris:
                uri_results = await search_by_author_uris(client, author_uris, api_key)
                all_articles.extend(uri_results)

            # Strategy 2: Keyword-based search
            keyword_results = await search_by_keyword(client, reporter_name, api_key)
            all_articles.extend(keyword_results)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - return empty but don't cache
                return []
            raise
        except (httpx.RequestError, ValueError):
            # Network error or invalid JSON - return empty
            return []

    # Deduplicate
    unique_articles = deduplicate_articles(all_articles)

    # Parse into our format
    parsed = parse_articles(unique_articles)

    # Filter to articles likely BY the author
    filtered = filter_by_author_name(parsed, reporter_name)

    # Sort by date descending
    filtered.sort(key=lambda a: a.get("date", ""), reverse=True)

    # Cache the results
    set_cached_query(reporter_name, filtered)

    return filtered
