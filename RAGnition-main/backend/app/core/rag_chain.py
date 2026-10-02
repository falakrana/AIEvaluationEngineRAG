"""
rag_chain.py
============
LLM abstraction layer + retrieval-augmented generation with SSE streaming.

Design:
  - LLMInterface: a simple Protocol so the LLM is swappable without
    touching the chain logic (GroqLLM, GeminiLLM, etc.).
  - GroqLLM: fast async streaming implementation using Groq.
  - GeminiLLM: fallback concrete implementation using ChatGoogleGenerativeAI.
  - run_rag_stream(): the main async generator that drives the full RAG loop
    and yields SSE-formatted event strings.

SSE event protocol used by the chat endpoint:
  event: token
  data: <text fragment>

  event: sources
  data: <JSON array of SourceChunk>

  event: done
  data: [DONE]
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Protocol, runtime_checkable

from groq import AsyncGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings
from app.core.document_store import get_retriever
from app.models.schemas import SourceChunk, Turn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a precise document assistant. Your job is to answer the user's \
question strictly based on the provided document context.

Rules:
1. Only use information present in the CONTEXT sections below.
2. If the context does not contain enough information, say so clearly — \
   do not invent facts.
3. When you reference information, naturally mention the page number(s) \
   it comes from (e.g., "According to page 3, ...").
4. Be concise but thorough.
5. If the user asks a follow-up question, use the conversation history \
   to maintain coherence.
"""

# ---------------------------------------------------------------------------
# LLM Protocol & Implementations
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMInterface(Protocol):
    """
    Minimal protocol for an LLM backend.
    Implementations must provide astream() which takes a list of
    LangChain message objects and yields string tokens.
    """

    async def astream(self, messages: list) -> AsyncIterator[str]:
        ...


class GroqLLM:
    """
    Wraps Groq Async client with streaming enabled.
    Satisfies LLMInterface.
    """

    def __init__(self):
        settings = get_settings()
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    async def astream(self, messages: list) -> AsyncIterator[str]:
        formatted_messages = []
        for msg in messages:
            role = "user"
            if isinstance(msg, SystemMessage) or getattr(msg, "type", "") == "system":
                role = "system"
            elif isinstance(msg, AIMessage) or getattr(msg, "type", "") == "ai":
                role = "assistant"
            formatted_messages.append({"role": role, "content": msg.content})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=formatted_messages,
            stream=True,
            temperature=0.2,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta


class GeminiLLM:
    """
    Wraps ChatGoogleGenerativeAI with streaming enabled.
    Satisfies LLMInterface.
    """

    def __init__(self):
        settings = get_settings()
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            streaming=True,
            temperature=0.2,
        )

    async def astream(self, messages: list) -> AsyncIterator[str]:
        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_messages(
    query: str,
    context_blocks: list[tuple[str, int]],   # (chunk_text, page_number)
    history: list[Turn],
) -> list:
    """
    Assemble the full message list for the LLM:
      1. System instruction
      2. Retrieved context (injected as a system-level block)
      3. Conversation history (up to last 10 turns to bound prompt size)
      4. Current user query
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Inject retrieved context as a separate system message so it doesn't
    # get confused with conversation history.
    if context_blocks:
        context_text = "\n\n".join(
            f"[Page {page}]\n{text}" for text, page in context_blocks
        )
        messages.append(
            SystemMessage(content=f"CONTEXT (from the uploaded document):\n\n{context_text}")
        )

    # Include the last 10 turns of conversation history
    for turn in history[-10:]:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        else:
            messages.append(AIMessage(content=turn.content))

    # Current query
    messages.append(HumanMessage(content=query))
    return messages


# ---------------------------------------------------------------------------
# Main RAG streaming generator
# ---------------------------------------------------------------------------

async def run_rag_stream(
    document_id: str,
    query: str,
    history: list[Turn],
    llm: LLMInterface | None = None,
):
    """
    Async generator that performs the full RAG loop and yields
    SSE-formatted event strings.

    Yields:
      "event: token\ndata: <fragment>\n\n"   — for each streamed token
      "event: sources\ndata: <json>\n\n"     — sources list at the end
      "event: done\ndata: [DONE]\n\n"         — terminal event
    """
    if llm is None:
        llm = GroqLLM()

    settings = get_settings()

    # 1. Retrieve relevant chunks
    retriever = get_retriever(document_id, k=settings.top_k)
    retrieved_docs = await retriever.ainvoke(query)

    # 2. Build context blocks from retrieved docs (preserve page metadata)
    context_blocks: list[tuple[str, int]] = []
    source_chunks: list[SourceChunk] = []

    for doc in retrieved_docs:
        page_num = doc.metadata.get("source_page", 1)
        chunk_id = doc.metadata.get("chunk_id", "unknown")
        snippet = doc.page_content.replace("\n", " ")

        context_blocks.append((doc.page_content, page_num))
        source_chunks.append(
            SourceChunk(
                chunk_id=chunk_id,
                page_number=page_num,
                snippet=snippet,
            )
        )

    logger.info(
        "Retrieved %d chunks for document_id=%r query=%r",
        len(retrieved_docs),
        document_id,
        query[:80],
    )

    # 3. Build LLM messages
    messages = _build_messages(query, context_blocks, history)

    # 4. Stream tokens
    try:
        async for token in llm.astream(messages):
            # Escape newlines inside the SSE data field
            safe_token = token.replace("\n", "\\n")
            yield f"event: token\ndata: {safe_token}\n\n"
    except Exception as exc:
        logger.exception("LLM streaming error: %s", exc)
        yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
        return

    # 5. Send sources as final event
    sources_payload = [s.model_dump() for s in source_chunks]
    yield f"event: sources\ndata: {json.dumps(sources_payload)}\n\n"

    # 6. Terminal event
    yield "event: done\ndata: [DONE]\n\n"
