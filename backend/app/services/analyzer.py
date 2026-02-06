"""Outlet history analysis and change detection."""

from collections import Counter
from datetime import date, timedelta
from typing import List, Optional, Tuple


def most_common_outlet(articles: List[dict]) -> Optional[str]:
    """Get the most common outlet from a list of articles."""
    if not articles:
        return None
    outlet_counts = Counter(a["outlet"] for a in articles)
    most_common = outlet_counts.most_common(1)
    return most_common[0][0] if most_common else None


def detect_outlet_change(articles: List[dict]) -> Tuple[bool, Optional[str]]:
    """Detect if reporter has changed primary outlet.

    Compares articles from the last 6 months vs the prior 6 months.
    If the primary outlet differs, flags a potential change.
    """
    if len(articles) < 5:
        # Not enough data to detect changes
        return False, None

    today = date.today()
    six_months_ago = today - timedelta(days=180)

    # Parse dates and split into recent/older
    recent = []
    older = []

    for article in articles:
        article_date = article["date"]
        if isinstance(article_date, str):
            article_date = date.fromisoformat(article_date)

        if article_date >= six_months_ago:
            recent.append(article)
        else:
            older.append(article)

    # Need articles in both periods to detect change
    if len(recent) < 2 or len(older) < 2:
        return False, None

    recent_primary = most_common_outlet(recent)
    older_primary = most_common_outlet(older)

    if recent_primary and older_primary and recent_primary != older_primary:
        # Count how dominant the outlets are
        recent_counts = Counter(a["outlet"] for a in recent)
        older_counts = Counter(a["outlet"] for a in older)

        recent_pct = recent_counts[recent_primary] / len(recent) * 100
        older_pct = older_counts[older_primary] / len(older) * 100

        # Only flag if the outlets were dominant in their periods
        if recent_pct >= 40 and older_pct >= 40:
            return True, f"Possible outlet change: Previously {older_primary}, now {recent_primary}"

    return False, None
