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

    # Reporter profiles (cache-first architecture)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reporters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            perigon_journalist_id TEXT,
            current_outlet TEXT,
            reporter_bio TEXT,
            social_links_json TEXT,
            source TEXT DEFAULT 'perigon',
            last_updated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: add source column to existing databases
    try:
        cursor.execute("ALTER TABLE reporters ADD COLUMN source TEXT DEFAULT 'perigon'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Articles linked to reporters
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            headline TEXT,
            outlet TEXT,
            date TEXT,
            url TEXT UNIQUE,
            summary TEXT,
            topics_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_id) REFERENCES reporters(id)
        )
    """)

    # Indexes for fast lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reporters_name ON reporters(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_reporter_id ON articles(reporter_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_reporter_date ON articles(reporter_id, date)")

    conn.commit()
    conn.close()


# Initialize on import
init_db()
