# Madison Mentions

Reporter intelligence tool for PR professionals. Enter a reporter name and get a dossier showing recent bylines, outlet history, and outlet change detection.

## Quick Start

1. **Set up the backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env and add your API keys:
# - ANTHROPIC_API_KEY: Your Anthropic API key for Claude Haiku
# - NEWSAPI_API_KEY: Your NewsAPI.ai API key (get one at https://newsapi.ai)
```

3. **Run the server:**

```bash
cd backend
uvicorn app.main:app --reload
```

4. **Open browser:**

Navigate to http://localhost:8000

## Features

- **Reporter Search**: Enter any reporter name to find their recent articles
- **Article Summaries**: AI-generated summaries of each article's topic/beat
- **Outlet History**: See which outlets the reporter writes for most frequently
- **Outlet Change Detection**: Automatic alerts when a reporter changes their primary outlet

## API

### `GET /api/reporter/{name}`

Returns a comprehensive dossier for the specified reporter.

**Example Response:**
```json
{
  "reporter_name": "Michael Rapoport",
  "query_date": "2025-02-05",
  "articles": [
    {
      "headline": "SEC Proposes New Disclosure Rules",
      "outlet": "Wall Street Journal",
      "date": "2025-01-15",
      "url": "https://...",
      "summary": "Examines new SEC disclosure requirements"
    }
  ],
  "outlet_history": [
    { "outlet": "Wall Street Journal", "count": 18 }
  ],
  "outlet_change_detected": false,
  "outlet_change_note": null
}
```

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: Vanilla HTML/CSS/JS
- **APIs**: NewsAPI.ai (Event Registry), Claude Haiku
- **Database**: SQLite (caching)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude Haiku |
| `NEWSAPI_API_KEY` | Your NewsAPI.ai API key |

## NewsAPI.ai

This app uses [NewsAPI.ai](https://newsapi.ai) for article data. The free tier provides:
- 2,000 searches per month
- Native author/byline filtering
- 150,000+ sources
- Data back to 2014

This is sufficient for MVP development and initial user testing.
