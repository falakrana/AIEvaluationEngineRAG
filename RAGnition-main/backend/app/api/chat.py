"""
chat.py
=======
POST /api/chat — streams an SSE response for a RAG-grounded query.

SSE event protocol:
  event: token   — one per streamed LLM token
  event: sources — JSON array of SourceChunk objects (final)
  event: error   — JSON error object if something goes wrong mid-stream
  event: done    — terminal sentinel
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.document_store import document_exists
from app.core.rag_chain import run_rag_stream
from app.models.schemas import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    summary="Ask a question about an uploaded document",
    description=(
        "Streams the answer as Server-Sent Events. "
        "Send `document_id` (from /api/upload) and your `query`. "
        "Optionally include `conversation_history` for multi-turn context. "
        "The stream emits `token`, `sources`, and `done` events."
    ),
    responses={
        200: {"description": "SSE stream (text/event-stream)"},
        404: {"description": "document_id not found"},
        422: {"description": "Validation error"},
    },
)
async def chat(request: ChatRequest) -> StreamingResponse:
    # ---- Validate document exists ----------------------------------------
    if not document_exists(request.document_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Document '{request.document_id}' not found. "
                "Please upload the document first via POST /api/upload."
            ),
        )

    # ---- Validate query is not blank -------------------------------------
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query must not be empty or whitespace only.",
        )

    logger.info(
        "Chat request: document_id=%r query=%r history_turns=%d",
        request.document_id,
        request.query[:80],
        len(request.conversation_history),
    )

    # ---- Return streaming SSE response -----------------------------------
    async def event_generator():
        try:
            async for sse_event in run_rag_stream(
                document_id=request.document_id,
                query=request.query,
                history=request.conversation_history,
            ):
                yield sse_event
        except FileNotFoundError as exc:
            import json
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
        except Exception as exc:
            import json
            logger.exception("Unexpected error in RAG stream: %s", exc)
            yield f"event: error\ndata: {json.dumps({'detail': 'Internal server error during generation.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevent buffering in proxies / nginx
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
