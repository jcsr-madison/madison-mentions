"""Pydantic models for Madison Mentions API."""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class Article(BaseModel):
    """A single article by a reporter."""
    headline: str
    outlet: str
    date: date
    url: str
    summary: Optional[str] = None


class OutletCount(BaseModel):
    """Outlet with article count."""
    outlet: str
    count: int


class ReporterDossier(BaseModel):
    """Complete dossier for a reporter."""
    reporter_name: str
    query_date: date
    articles: List[Article]
    outlet_history: List[OutletCount]
    outlet_change_detected: bool
    outlet_change_note: Optional[str] = None
