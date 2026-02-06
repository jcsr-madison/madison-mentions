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
    current_outlet: Optional[str] = None
    reporter_bio: Optional[str] = None
    social_links: Optional[SocialLinks] = None
    outlet_change_detected: bool
    outlet_change_note: Optional[str] = None
