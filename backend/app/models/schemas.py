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
    topics: List[str] = []


class OutletCount(BaseModel):
    """Outlet with article count."""
    outlet: str
    count: int


class BeatCount(BaseModel):
    """Topic/beat with article count."""
    beat: str
    count: int


class SocialLinks(BaseModel):
    """Social media and professional links for a reporter."""
    twitter_handle: Optional[str] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    title: Optional[str] = None  # e.g., "Senior Political Correspondent, NYT"


class ReporterDossier(BaseModel):
    """Complete dossier for a reporter."""
    reporter_name: str
    query_date: date
    articles: List[Article]
    outlet_history: List[OutletCount]
    primary_beats: List[BeatCount]
    social_links: Optional[SocialLinks] = None
    outlet_change_detected: bool
    outlet_change_note: Optional[str] = None


class JournalistSummary(BaseModel):
    """Summary of a journalist for search results."""
    name: str
    title: Optional[str] = None
    outlets: List[str] = []
    twitter_handle: Optional[str] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    article_count: int = 0


class JournalistSearchResponse(BaseModel):
    """Response for journalist search by topic."""
    topic: str
    query_date: date
    total_results: int
    journalists: List[JournalistSummary]
