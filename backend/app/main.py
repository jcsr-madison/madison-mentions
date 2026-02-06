"""Madison Mentions - Reporter Intelligence Tool.

FastAPI application entry point.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import reporters, csv_import


app = FastAPI(
    title="Madison Mentions",
    description="Reporter intelligence tool for PR professionals",
    version="1.0.0"
)

# Include API routes
app.include_router(reporters.router)
app.include_router(csv_import.router)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"


@app.get("/")
async def serve_index():
    """Serve the main frontend page."""
    return FileResponse(frontend_path / "index.html")


@app.get("/styles.css")
async def serve_styles():
    """Serve CSS file."""
    return FileResponse(frontend_path / "styles.css", media_type="text/css")


@app.get("/app.js")
async def serve_js():
    """Serve JavaScript file."""
    return FileResponse(frontend_path / "app.js", media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
