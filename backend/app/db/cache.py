"""Caching layer for NewsAPI.ai queries and article summaries."""

import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from .database import get_connection


QUERY_CACHE_TTL_HOURS = 24


def get_cached_query(reporter_name: str) -> Optional[List[dict]]:
    """Get cached query result if fresh (within TTL)."""
    conn = get_connection()
    cursor = conn.cursor()

    cutoff = datetime.now() - timedelta(hours=QUERY_CACHE_TTL_HOURS)

    cursor.execute("""
        SELECT result_json FROM cached_queries
        WHERE reporter_name = ? AND created_at > ?
        ORDER BY created_at DESC LIMIT 1
    """, (reporter_name.lower(), cutoff.isoformat()))

    row = cursor.fetchone()
    conn.close()

    if row:
        return json.loads(row["result_json"])
    return None


def set_cached_query(reporter_name: str, articles: List[dict]):
    """Cache query result."""
    conn = get_connection()
    cursor = conn.cursor()

    today = date.today().isoformat()
    result_json = json.dumps(articles)

    cursor.execute("""
        INSERT OR REPLACE INTO cached_queries (reporter_name, query_date, result_json)
        VALUES (?, ?, ?)
    """, (reporter_name.lower(), today, result_json))

    conn.commit()
    conn.close()


def get_cached_summary(article_url: str) -> Optional[str]:
    """Get cached summary for an article URL."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT summary FROM cached_summaries WHERE article_url = ?
    """, (article_url,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return row["summary"]
    return None


def set_cached_summary(article_url: str, summary: str):
    """Cache summary for an article URL."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO cached_summaries (article_url, summary)
        VALUES (?, ?)
    """, (article_url, summary))

    conn.commit()
    conn.close()


def get_cached_summaries_bulk(article_urls: List[str]) -> Dict[str, str]:
    """Get cached summaries for multiple URLs at once."""
    if not article_urls:
        return {}

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" * len(article_urls))
    cursor.execute(f"""
        SELECT article_url, summary FROM cached_summaries
        WHERE article_url IN ({placeholders})
    """, article_urls)

    results = {row["article_url"]: row["summary"] for row in cursor.fetchall()}
    conn.close()

    return results


def set_cached_summaries_bulk(summaries: Dict[str, str]):
    """Cache multiple summaries at once."""
    if not summaries:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR REPLACE INTO cached_summaries (article_url, summary)
        VALUES (?, ?)
    """, list(summaries.items()))

    conn.commit()
    conn.close()
