"""Data access layer for the reporters and articles tables."""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .database import get_connection


FRESHNESS_WINDOW_DAYS = 7


def get_reporter(name: str) -> Optional[Dict]:
    """Lookup reporter by lowercase-trimmed name. Returns dict or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reporters WHERE name = ?",
        (name.strip().lower(),),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def is_reporter_fresh(reporter: Dict) -> bool:
    """Check if reporter record is within the freshness window."""
    last_updated = reporter.get("last_updated")
    if not last_updated:
        return False
    if isinstance(last_updated, str):
        last_updated = datetime.fromisoformat(last_updated)
    return datetime.now() - last_updated < timedelta(days=FRESHNESS_WINDOW_DAYS)


def get_reporter_articles(reporter_id: int) -> List[Dict]:
    """Return all articles for a reporter, sorted by date DESC, with parsed topics."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM articles WHERE reporter_id = ? ORDER BY date DESC",
        (reporter_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    articles = []
    for row in rows:
        article = dict(row)
        try:
            article["topics"] = json.loads(article.get("topics_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            article["topics"] = []
        articles.append(article)
    return articles


def get_latest_article_date(reporter_id: int) -> Optional[str]:
    """Return the most recent article date for a reporter, or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(date) as max_date FROM articles WHERE reporter_id = ?",
        (reporter_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row and row["max_date"]:
        return row["max_date"]
    return None


def upsert_reporter(
    name: str,
    perigon_id: Optional[str] = None,
    social_links: Optional[Dict] = None,
    current_outlet: Optional[str] = None,
    bio: Optional[str] = None,
    source: Optional[str] = None,
) -> int:
    """Insert or update a reporter record. Returns the reporter id."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    social_json = json.dumps(social_links) if social_links else None

    cursor.execute(
        """
        INSERT INTO reporters (name, perigon_journalist_id, social_links_json, current_outlet, reporter_bio, source, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            perigon_journalist_id = COALESCE(excluded.perigon_journalist_id, perigon_journalist_id),
            social_links_json = COALESCE(excluded.social_links_json, social_links_json),
            current_outlet = COALESCE(excluded.current_outlet, current_outlet),
            reporter_bio = COALESCE(excluded.reporter_bio, reporter_bio),
            source = COALESCE(excluded.source, source),
            last_updated = excluded.last_updated
        """,
        (name.strip().lower(), perigon_id, social_json, current_outlet, bio, source, now),
    )
    reporter_id = cursor.lastrowid

    # If ON CONFLICT triggered, lastrowid may be 0; fetch the actual id
    if not reporter_id:
        cursor.execute("SELECT id FROM reporters WHERE name = ?", (name.strip().lower(),))
        reporter_id = cursor.fetchone()["id"]

    conn.commit()
    conn.close()
    return reporter_id


def insert_articles(reporter_id: int, articles: List[Dict]) -> int:
    """Insert articles, skipping duplicates by URL. Returns count of new inserts."""
    if not articles:
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for a in articles:
        topics_json = json.dumps(a.get("topics", []))
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO articles
                    (reporter_id, headline, outlet, date, url, summary, topics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reporter_id,
                    a.get("headline"),
                    a.get("outlet"),
                    a.get("date"),
                    a.get("url"),
                    a.get("summary"),
                    topics_json,
                ),
            )
            if cursor.rowcount > 0:
                inserted += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    return inserted


def update_reporter_profile(
    reporter_id: int,
    current_outlet: Optional[str] = None,
    bio: Optional[str] = None,
) -> None:
    """Update the profile fields and touch last_updated."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        """
        UPDATE reporters
        SET current_outlet = ?, reporter_bio = ?, last_updated = ?
        WHERE id = ?
        """,
        (current_outlet, bio, now, reporter_id),
    )
    conn.commit()
    conn.close()


def update_reporter_timestamp(reporter_id: int) -> None:
    """Touch last_updated without changing other fields."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        "UPDATE reporters SET last_updated = ? WHERE id = ?",
        (now, reporter_id),
    )
    conn.commit()
    conn.close()
