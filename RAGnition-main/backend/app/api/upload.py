"""
upload.py
=========
POST /api/upload — accepts a PDF or TXT file, runs the ingest pipeline,
returns document metadata. The uploaded file is cleaned up after ingestion.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.document_store import ingest_document
from app.models.schemas import UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a document for analysis",
    description=(
        "Accepts a PDF or plain-text file. Extracts text per page, chunks it, "
        "embeds it with Google Generative AI Embeddings, and persists the "
        "resulting vector store. Returns a `document_id` needed for chat queries."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    settings = get_settings()

    # ---- Validate file type -----------------------------------------------
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type {suffix!r}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # ---- Validate file size -----------------------------------------------
    contents = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File exceeds maximum allowed size of {settings.max_file_size_mb} MB."
            ),
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    # ---- Save to a temp location under storage/uploads --------------------
    # Use a UUID subdirectory to avoid filename collisions
    upload_subdir = settings.upload_dir / str(uuid.uuid4())
    upload_subdir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_subdir / filename

    try:
        temp_path.write_bytes(contents)
        logger.info("Saved upload to %s (%d bytes)", temp_path, len(contents))

        # ---- Run the ingest pipeline --------------------------------------
        result = ingest_document(file_path=temp_path, filename=filename)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Ingestion failed for %r: %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {exc}",
        )
    finally:
        # ---- Clean up temp file (Chroma dir stays) -----------------------
        if temp_path.exists():
            temp_path.unlink()
        if upload_subdir.exists():
            try:
                upload_subdir.rmdir()
            except OSError:
                pass  # non-empty dir — leave it (shouldn't happen)

    return result
