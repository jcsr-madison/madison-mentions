"""Claude Haiku summarization service for article headlines."""

import os
from typing import Dict, List

import anthropic
from dotenv import load_dotenv

from ..db.cache import get_cached_summaries_bulk, set_cached_summaries_bulk


load_dotenv()

# Use Haiku for cost efficiency
MODEL = "claude-3-haiku-20240307"


def get_client() -> anthropic.Anthropic:
    """Get Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


MAX_ARTICLES_TO_SUMMARIZE = 20  # Limit to reduce cold-start latency


async def summarize_headlines(articles: List[dict]) -> List[dict]:
    """Add summaries to articles using Claude Haiku.

    Uses caching to avoid redundant API calls.
    Only summarizes top 20 articles to keep response times fast.
    """
    if not articles:
        return articles

    # Get URLs that need summarization
    urls = [a["url"] for a in articles]
    cached_summaries = get_cached_summaries_bulk(urls)

    # Find which articles need new summaries
    articles_to_summarize = []
    for article in articles:
        if article["url"] in cached_summaries:
            article["summary"] = cached_summaries[article["url"]]
        else:
            articles_to_summarize.append(article)

    # Limit to top N articles to reduce cold-start latency
    # Remaining articles use headline as summary
    if len(articles_to_summarize) > MAX_ARTICLES_TO_SUMMARIZE:
        for article in articles_to_summarize[MAX_ARTICLES_TO_SUMMARIZE:]:
            article["summary"] = article["headline"]
        articles_to_summarize = articles_to_summarize[:MAX_ARTICLES_TO_SUMMARIZE]

    if not articles_to_summarize:
        return articles

    # Summarize uncached articles in batch
    try:
        client = get_client()
        new_summaries = {}

        # Process in batches of 10 to avoid token limits
        batch_size = 10
        for i in range(0, len(articles_to_summarize), batch_size):
            batch = articles_to_summarize[i:i + batch_size]

            # Build batch prompt
            headlines_text = "\n".join(
                f"{j+1}. [{a['outlet']}] {a['headline']}"
                for j, a in enumerate(batch)
            )

            prompt = f"""Summarize each of these news article headlines in one concise sentence each.
Focus on what the article is about and what beat/topic it covers.
Write for a PR professional researching the reporter.

Headlines:
{headlines_text}

Provide exactly {len(batch)} summaries, numbered to match the headlines above.
Keep each summary to one sentence, under 100 characters if possible."""

            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response - extract summaries
            response_text = response.content[0].text
            lines = [l.strip() for l in response_text.strip().split("\n") if l.strip()]

            # Match summaries to articles
            summary_idx = 0
            for line in lines:
                # Skip lines that don't look like numbered summaries
                if not line[0].isdigit():
                    continue
                # Remove number prefix
                summary = line.lstrip("0123456789.)-: ")
                if summary and summary_idx < len(batch):
                    article = batch[summary_idx]
                    article["summary"] = summary
                    new_summaries[article["url"]] = summary
                    summary_idx += 1

            # Handle any articles that didn't get summaries
            for j in range(summary_idx, len(batch)):
                batch[j]["summary"] = batch[j]["headline"][:100]

        # Cache new summaries
        if new_summaries:
            set_cached_summaries_bulk(new_summaries)

    except (anthropic.APIError, ValueError) as e:
        # If summarization fails, use headline as fallback
        for article in articles_to_summarize:
            if "summary" not in article or not article["summary"]:
                article["summary"] = article["headline"][:100]

    return articles
