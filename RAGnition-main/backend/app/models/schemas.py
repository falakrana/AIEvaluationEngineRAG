"""
Pydantic v2 request/response models for the Document AI Assistant API.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / nested models
# ---------------------------------------------------------------------------

class Turn(BaseModel):
    """A single turn in the conversation history."""
    role: Literal["user", "assistant"]
    content: str


class SourceChunk(BaseModel):
    """A single retrieved chunk that was used to ground the answer."""
    chunk_id: str
    page_number: int  # 1-indexed, human-readable
    snippet: str = Field(..., description="First 300 chars of the chunk text")


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    num_pages: int
    num_chunks: int


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1, max_length=4096)
    conversation_history: list[Turn] = Field(
        default_factory=list,
        description="Prior turns sent by the client so the server can be stateless.",
    )


class ChatResponse(BaseModel):
    """Sent as the final SSE 'sources' event payload (JSON-encoded)."""
    answer: str
    sources: list[SourceChunk]


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
