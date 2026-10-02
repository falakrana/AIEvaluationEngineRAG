"""
document_store.py
=================
Handles the full ingest pipeline:
  1. Load PDF (per-page) or plain text with page metadata preserved.
  2. Chunk with RecursiveCharacterTextSplitter — page_number carried forward.
  3. Embed with GoogleGenerativeAIEmbeddings.
  4. Persist to a per-document Chroma collection.

Also exposes get_retriever() to open an existing collection for chat.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever

from app.core.config import get_settings
from app.models.schemas import UploadResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_pdf(file_path: Path) -> List[Document]:
    """
    Load a PDF file using PyPDFLoader.
    Returns one Document per page; metadata["page"] is 0-indexed (set by loader).
    We add "source_page" (1-indexed) for display purposes.
    """
    loader = PyPDFLoader(str(file_path))
    pages: List[Document] = loader.load()
    for doc in pages:
        # PyPDFLoader sets metadata["page"] as 0-indexed integer
        doc.metadata["source_page"] = doc.metadata.get("page", 0) + 1
    return pages


def _load_txt(file_path: Path) -> List[Document]:
    """
    Load a plain-text file as a single 'page'.
    """
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return [Document(page_content=text, metadata={"page": 0, "source_page": 1})]


def _chunk_documents(
    pages: List[Document],
    chunk_size: int,
    chunk_overlap: int,
    document_id: str,
) -> List[Document]:
    """
    Split page-level Documents into smaller chunks.

    Page metadata is propagated automatically by split_documents().
    We additionally inject:
      - chunk_id   : unique string identifier for this chunk
      - source_page: 1-indexed page number (inherited from parent Document)

    This is the critical link that makes citations possible later:
    every chunk knows which page it came from.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks: List[Document] = splitter.split_documents(pages)

    for idx, chunk in enumerate(chunks):
        page_num = chunk.metadata.get("source_page", 1)
        chunk.metadata["chunk_id"] = f"{document_id}-p{page_num}-c{idx}"
        # Ensure source_page is always present even after splitting
        chunk.metadata.setdefault("source_page", 1)

    return chunks


def _get_embedding():
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )


def _chroma_collection_path(document_id: str) -> str:
    """Return the filesystem path for a document's Chroma persistence dir."""
    settings = get_settings()
    return str(settings.chroma_dir / document_id)


def _collection_name(document_id: str) -> str:
    return f"doc_{document_id}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_document(file_path: Path, filename: str) -> UploadResponse:
    """
    Full ingestion pipeline for a single document.

    Steps:
      1. Assign a UUID document_id.
      2. Load the file (PDF or TXT) into per-page Documents.
      3. Chunk while preserving page metadata.
      4. Embed and write to a persistent Chroma collection.

    The upload file is NOT deleted here — the caller (API route) is responsible
    for cleanup so errors don't swallow the file silently.
    """
    settings = get_settings()
    document_id = str(uuid.uuid4())

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        pages = _load_pdf(file_path)
    elif suffix == ".txt":
        pages = _load_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix!r}")

    num_pages = len(pages)
    logger.info(
        "Loaded %d page(s) from %r (document_id=%s)", num_pages, filename, document_id
    )

    chunks = _chunk_documents(
        pages,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        document_id=document_id,
    )
    num_chunks = len(chunks)
    logger.info("Created %d chunks for document_id=%s", num_chunks, document_id)

    embedding = _get_embedding()
    persist_path = _chroma_collection_path(document_id)

    Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=persist_path,
        collection_name=_collection_name(document_id),
    )
    logger.info(
        "Persisted Chroma collection to %r (document_id=%s)", persist_path, document_id
    )

    return UploadResponse(
        document_id=document_id,
        filename=filename,
        num_pages=num_pages,
        num_chunks=num_chunks,
    )


def get_retriever(document_id: str, k: int | None = None) -> VectorStoreRetriever:
    """
    Open the persisted Chroma collection for the given document_id and
    return a retriever.

    Raises FileNotFoundError if the collection directory does not exist
    (i.e., the document was never ingested or has been deleted).
    """
    settings = get_settings()
    k = k or settings.top_k

    persist_path = _chroma_collection_path(document_id)
    if not Path(persist_path).exists():
        raise FileNotFoundError(
            f"No Chroma collection found for document_id={document_id!r}. "
            "Please upload the document first."
        )

    embedding = _get_embedding()
    vector_store = Chroma(
        persist_directory=persist_path,
        collection_name=_collection_name(document_id),
        embedding_function=embedding,
    )
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


def document_exists(document_id: str) -> bool:
    """Quick check: does a Chroma collection exist for this document_id?"""
    persist_path = _chroma_collection_path(document_id)
    return Path(persist_path).exists()
