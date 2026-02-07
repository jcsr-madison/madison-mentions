"""Claude Haiku service for classifying reporter relevance to professional services."""

import json
import os
from typing import List, Set, Tuple

import anthropic
from dotenv import load_dotenv


load_dotenv()

MODEL = "claude-3-haiku-20240307"

# Keywords for fallback heuristic
RELEVANCE_KEYWORDS = [
    "law", "accounting", "tax", "consulting", "m&a", "audit",
    "compliance", "advisory", "cfo", "legal", "regulation",
    "finance", "banking", "private equity", "venture capital",
    "restructuring", "litigation", "governance", "fiduciary",
]


def get_client() -> anthropic.Anthropic:
    """Get Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def classify_reporter(
    reporter_name: str,
    outlets: Set[str],
    article_summaries: List[str],
) -> Tuple[bool, str]:
    """Classify whether a reporter is relevant to professional services.

    Returns (relevant: bool, rationale: str).
    Falls back to keyword heuristic on API failure.
    """
    # Limit to 10 summaries
    summaries = article_summaries[:10]
    outlets_text = ", ".join(outlets) if outlets else "Unknown"
    summaries_text = "\n".join(f"- {s}" for s in summaries)

    prompt = f"""You are classifying a journalist for a PR tool used by professional services firms (law, accounting, consulting, financial advisory).

Reporter: {reporter_name}
Outlets: {outlets_text}

Recent article summaries:
{summaries_text}

Question: Is this reporter relevant to professional services firms? A relevant reporter covers topics like: legal industry, accounting/audit, tax policy, M&A/deals, management consulting, financial regulation, corporate governance, bankruptcy/restructuring, or business topics where professional services firms are key players.

Respond in this exact JSON format:
{{"relevant": true, "rationale": "One sentence explaining why."}}

If the reporter primarily covers sports, entertainment, lifestyle, weather, local crime, or other unrelated beats, mark them as not relevant."""

    try:
        client = get_client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text.strip()

        # Strip markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        data = json.loads(response_text)
        relevant = bool(data.get("relevant", False))
        rationale = data.get("rationale", "")
        return relevant, rationale

    except (anthropic.APIError, json.JSONDecodeError, ValueError, KeyError):
        return _fallback_classify(outlets, article_summaries)


def _fallback_classify(
    outlets: Set[str],
    article_summaries: List[str],
) -> Tuple[bool, str]:
    """Keyword-based fallback when Claude API is unavailable."""
    text = " ".join(article_summaries).lower() + " " + " ".join(outlets).lower()
    matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text)

    if matches >= 3:
        return True, "Keyword-based classification: multiple professional services terms found in recent coverage."
    return False, "Keyword-based classification: few professional services terms found in recent coverage."
