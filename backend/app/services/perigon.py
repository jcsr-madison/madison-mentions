"""Perigon API client for fetching reporter bylines.

Perigon has excellent journalist coverage (230K+ journalists) with proper
author attribution. This is the primary data source for Madison Mentions.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from dotenv import load_dotenv

from ..db.cache import get_cached_query, set_cached_query


load_dotenv()

PERIGON_BASE_URL = "https://api.goperigon.com/v1"
REQUEST_TIMEOUT = 30.0


def get_api_key() -> str:
    """Get Perigon API key from environment."""
    api_key = os.getenv("PERIGON_API_KEY")
    if not api_key:
        raise ValueError("PERIGON_API_KEY environment variable not set")
    return api_key


async def search_journalist(
    client: httpx.AsyncClient,
    reporter_name: str,
    api_key: str
) -> Optional[str]:
    """Search for a journalist by name and return their ID."""
    try:
        response = await client.get(
            f"{PERIGON_BASE_URL}/journalists",
            params={
                "name": reporter_name,
                "apiKey": api_key
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            return None

        # Return the first matching journalist's ID
        # Could improve by matching on exact name if multiple results
        return results[0].get("id")

    except Exception:
        return None


async def fetch_articles_by_journalist(
    client: httpx.AsyncClient,
    journalist_id: str,
    api_key: str
) -> List[dict]:
    """Fetch recent articles by a journalist ID."""
    try:
        # Get articles from the last 12 months
        from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        response = await client.get(
            f"{PERIGON_BASE_URL}/all",
            params={
                "journalistId": journalist_id,
                "from": from_date,
                "sortBy": "date",
                "size": 100,
                "apiKey": api_key
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        return data.get("articles", [])

    except Exception:
        return []


def parse_article(item: dict) -> Optional[dict]:
    """Parse a single article from Perigon response."""
    try:
        url = item.get("url", "")
        title = item.get("title", "")

        if not url or not title:
            return None

        # Parse publication date
        pub_date = item.get("pubDate", "")
        if pub_date:
            try:
                # Perigon format: 2026-01-03T07:02:07+00:00
                article_date = datetime.fromisoformat(pub_date.replace("+00:00", "")).date()
            except ValueError:
                return None
        else:
            return None

        # Get source/outlet
        source = item.get("source", {})
        domain = source.get("domain", "Unknown")
        outlet = clean_outlet_name(domain)

        return {
            "headline": title,
            "outlet": outlet,
            "date": article_date.isoformat(),
            "url": url,
        }

    except (ValueError, KeyError, AttributeError):
        return None


def clean_outlet_name(domain: str) -> str:
    """Clean up domain name to display name."""
    if not domain:
        return "Unknown"

    # Map common domains to display names
    domain_map = {
        "nytimes.com": "New York Times",
        "wsj.com": "Wall Street Journal",
        "washingtonpost.com": "Washington Post",
        "politico.com": "Politico",
        "theatlantic.com": "The Atlantic",
        "bloomberg.com": "Bloomberg",
        "reuters.com": "Reuters",
        "apnews.com": "AP News",
        "cnn.com": "CNN",
        "foxnews.com": "Fox News",
        "nbcnews.com": "NBC News",
        "cbsnews.com": "CBS News",
        "abcnews.go.com": "ABC News",
        "usatoday.com": "USA Today",
        "latimes.com": "Los Angeles Times",
        "chicagotribune.com": "Chicago Tribune",
        "bostonglobe.com": "Boston Globe",
        "sfchronicle.com": "SF Chronicle",
        "axios.com": "Axios",
        "thehill.com": "The Hill",
        "businessinsider.com": "Business Insider",
        "forbes.com": "Forbes",
        "fortune.com": "Fortune",
        "theguardian.com": "The Guardian",
        "bbc.com": "BBC",
        "economist.com": "The Economist",
        "ft.com": "Financial Times",
        "marketwatch.com": "MarketWatch",
        "cnbc.com": "CNBC",
        "npr.org": "NPR",
        "time.com": "Time",
        "newyorker.com": "The New Yorker",
        "vanityfair.com": "Vanity Fair",
        "rollingstone.com": "Rolling Stone",
        "vox.com": "Vox",
        "slate.com": "Slate",
        "thedailybeast.com": "The Daily Beast",
        "huffpost.com": "HuffPost",
        "buzzfeednews.com": "BuzzFeed News",
    }

    if domain in domain_map:
        return domain_map[domain]

    # Fallback: clean up domain
    name = domain.replace("www.", "").split(".")[0]
    return name.title()


async def fetch_reporter_articles(reporter_name: str) -> List[dict]:
    """Fetch articles by reporter from Perigon, with caching.

    1. Search for journalist by name to get their ID
    2. Fetch articles by that journalist ID
    3. Parse and return results
    """
    # Check cache first
    cache_key = f"perigon:{reporter_name}"
    cached = get_cached_query(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            api_key = get_api_key()

            # Step 1: Find journalist ID
            journalist_id = await search_journalist(client, reporter_name, api_key)
            if not journalist_id:
                # No journalist found - cache empty result
                set_cached_query(cache_key, [])
                return []

            # Step 2: Fetch their articles
            raw_articles = await fetch_articles_by_journalist(client, journalist_id, api_key)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited
                return []
            raise
        except (httpx.RequestError, ValueError):
            return []

    # Step 3: Parse articles
    articles = []
    for item in raw_articles:
        parsed = parse_article(item)
        if parsed:
            articles.append(parsed)

    # Sort by date descending
    articles.sort(key=lambda a: a.get("date", ""), reverse=True)

    # Cache results
    set_cached_query(cache_key, articles)

    return articles
