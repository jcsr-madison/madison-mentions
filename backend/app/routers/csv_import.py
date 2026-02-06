"""CSV import endpoints — upload, AI analysis, and confirm import."""

import csv
import io
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from ..db.reporter_store import get_reporter, upsert_reporter
from ..services.csv_analyzer import analyze_csv_with_claude


router = APIRouter(prefix="/api", tags=["import"])

# In-memory store for pending imports (session_id -> data)
_pending_imports: Dict[str, dict] = {}

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_ROWS = 5000


class ConfirmRequest(BaseModel):
    session_id: str
    column_mapping: Dict[str, Optional[str]]
    skip_duplicates: bool = True


@router.post("/import/analyze")
async def analyze_csv(file: UploadFile):
    """Upload a CSV file and get AI-powered column mapping analysis."""
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    # Read and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File must be under 2 MB")

    if not contents.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    # Decode — try UTF-8-sig first, then latin-1
    text = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = contents.decode(encoding)
            break
        except (UnicodeDecodeError, ValueError):
            continue

    if text is None:
        raise HTTPException(status_code=400, detail="Could not decode file — unsupported encoding")

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames
    if not headers:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    rows = []
    for i, row in enumerate(reader):
        if i >= MAX_ROWS:
            break
        rows.append(row)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV has no data rows")

    # Prepare sample rows as lists (matching header order)
    sample_rows = [
        [row.get(h, "") for h in headers] for row in rows[:10]
    ]

    # AI analysis
    analysis = analyze_csv_with_claude(headers, sample_rows)

    # Detect duplicates by checking names against existing reporters
    duplicates = []
    name_col = None
    if analysis.get("column_mapping"):
        name_col = analysis["column_mapping"].get("name")
    if name_col:
        seen_names = set()
        for row in rows:
            name_val = (row.get(name_col) or "").strip()
            if name_val and name_val.lower() not in seen_names:
                seen_names.add(name_val.lower())
                existing = get_reporter(name_val)
                if existing:
                    duplicates.append(name_val)

    # Store pending import
    session_id = str(uuid.uuid4())
    _pending_imports[session_id] = {
        "rows": rows,
        "headers": list(headers),
        "analysis": analysis,
        "filename": file.filename,
    }

    return {
        "session_id": session_id,
        "filename": file.filename,
        "total_rows": len(rows),
        "headers": list(headers),
        "sample_rows": [dict(row) for row in rows[:5]],
        "analysis": analysis,
        "duplicates": duplicates,
    }


@router.post("/import/confirm")
async def confirm_import(request: ConfirmRequest):
    """Apply column mapping and import reporters into the database."""
    pending = _pending_imports.pop(request.session_id, None)
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Import session not found or expired. Please re-upload the file."
        )

    mapping = request.column_mapping
    name_col = mapping.get("name")
    if not name_col:
        raise HTTPException(status_code=400, detail="Name column mapping is required")

    outlet_col = mapping.get("outlet")
    bio_col = mapping.get("bio")
    twitter_col = mapping.get("twitter")
    linkedin_col = mapping.get("linkedin")

    imported = 0
    skipped = 0
    errors = 0

    for row in pending["rows"]:
        try:
            name = (row.get(name_col) or "").strip()
            if not name:
                skipped += 1
                continue

            # Skip duplicates if requested
            if request.skip_duplicates:
                existing = get_reporter(name)
                if existing:
                    skipped += 1
                    continue

            outlet = (row.get(outlet_col) or "").strip() if outlet_col else None
            bio = (row.get(bio_col) or "").strip() if bio_col else None

            # Build social links
            social_links = {}
            if twitter_col:
                twitter_val = (row.get(twitter_col) or "").strip()
                if twitter_val:
                    handle = twitter_val.lstrip("@")
                    # If it's already a URL, extract handle
                    if "twitter.com/" in handle or "x.com/" in handle:
                        social_links["twitter_url"] = twitter_val
                        handle = handle.split("/")[-1].split("?")[0]
                    else:
                        social_links["twitter_url"] = f"https://twitter.com/{handle}"
                    social_links["twitter_handle"] = handle

            if linkedin_col:
                linkedin_val = (row.get(linkedin_col) or "").strip()
                if linkedin_val:
                    if linkedin_val.startswith("http"):
                        social_links["linkedin_url"] = linkedin_val
                    else:
                        social_links["linkedin_url"] = f"https://linkedin.com/in/{linkedin_val}"

            upsert_reporter(
                name=name,
                social_links=social_links if social_links else None,
                current_outlet=outlet or None,
                bio=bio or None,
                source="csv_import",
            )
            imported += 1

        except Exception:
            errors += 1
            continue

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "total_rows": len(pending["rows"]),
    }
