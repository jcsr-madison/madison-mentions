"""SQLite database connection and initialization."""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent.parent / "madison_mentions.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Cache for GDELT query results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_name TEXT NOT NULL,
            query_date TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(reporter_name, query_date)
        )
    """)

    # Cache for article summaries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_url TEXT UNIQUE NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# Initialize on import
init_db()
