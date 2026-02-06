"""Claude Haiku service for analyzing CSV structure and mapping columns."""

import json
import os
from typing import Dict, List, Optional

import anthropic
from dotenv import load_dotenv


load_dotenv()

MODEL = "claude-3-haiku-20240307"


def get_client() -> anthropic.Anthropic:
    """Get Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def analyze_csv_with_claude(
    headers: List[str], sample_rows: List[List[str]]
) -> Dict:
    """Use Claude Haiku to analyze CSV structure and suggest column mappings.

    Returns dict with: column_mapping, normalizations, issues, confidence.
    """
    # Format as pipe-delimited table
    table_lines = [" | ".join(headers)]
    table_lines.append(" | ".join("---" for _ in headers))
    for row in sample_rows[:10]:
        table_lines.append(" | ".join(str(v) for v in row))
    table_text = "\n".join(table_lines)

    prompt = f"""You are analyzing a CSV file containing reporter/journalist contact data for a PR tool.

Here are the headers and first rows:

{table_text}

Analyze this data and return a JSON object with:

1. "column_mapping": Map each of these fields to the best matching CSV column header, or null if no match:
   - "name" (reporter's full name — REQUIRED)
   - "outlet" (news organization / publication)
   - "bio" (description, notes, or beat information)
   - "twitter" (Twitter/X handle or URL)
   - "linkedin" (LinkedIn URL or profile)

2. "normalizations": A list of strings describing cleanup actions you'd recommend (e.g., "Standardize outlet names", "Strip @ from Twitter handles")

3. "issues": A list of strings noting data quality warnings (e.g., "3 rows have empty names", "Twitter column has mixed formats")

4. "confidence": "high", "medium", or "low" — how confident you are in the mapping

Return ONLY valid JSON, no explanation."""

    try:
        client = get_client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text.strip()

        # Strip markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        return json.loads(response_text)

    except (anthropic.APIError, json.JSONDecodeError, ValueError, KeyError):
        return _fallback_mapping(headers)


def _fallback_mapping(headers: List[str]) -> Dict:
    """Naive keyword-based column mapping when Claude API is unavailable."""
    lower_headers = {h: h.lower() for h in headers}
    mapping = {
        "name": None,
        "outlet": None,
        "bio": None,
        "twitter": None,
        "linkedin": None,
    }

    for header, lower in lower_headers.items():
        if any(k in lower for k in ("name", "reporter", "journalist", "contact")):
            if not mapping["name"]:
                mapping["name"] = header
        elif any(k in lower for k in ("outlet", "publication", "org", "media", "paper", "newspaper")):
            if not mapping["outlet"]:
                mapping["outlet"] = header
        elif any(k in lower for k in ("bio", "description", "notes", "beat", "about")):
            if not mapping["bio"]:
                mapping["bio"] = header
        elif any(k in lower for k in ("twitter", "x.com", "handle")):
            if not mapping["twitter"]:
                mapping["twitter"] = header
        elif any(k in lower for k in ("linkedin",)):
            if not mapping["linkedin"]:
                mapping["linkedin"] = header

    return {
        "column_mapping": mapping,
        "normalizations": [],
        "issues": ["AI analysis unavailable — using basic column name matching"],
        "confidence": "low",
    }
