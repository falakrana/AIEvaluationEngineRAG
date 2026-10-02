import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

RAG_BACKEND_URL = os.getenv("RAG_BACKEND_URL", "http://localhost:8000")
DOCUMENT_ID = os.getenv("DOCUMENT_ID", "").strip()


def run_model(question: str, document_id: str | None = None, backend_url: str | None = None) -> dict:
    """
    Calls the RAGnition FastAPI backend (/api/chat) via SSE stream.
    Returns a dictionary with:
      - 'answer': The full LLM generated response string
      - 'sources': List of retrieved source chunks with page numbers and snippets
      - 'context': Extracted raw context texts for the LLM judge
    """
    doc_id = document_id or DOCUMENT_ID
    url = (backend_url or RAG_BACKEND_URL).rstrip("/") + "/api/chat"

    if not doc_id:
        raise ValueError(
            "DOCUMENT_ID is not set! Please upload the PDF to RAGnition first "
            "and set DOCUMENT_ID in your .env file or pass it to run_model()."
        )

    payload = {
        "document_id": doc_id,
        "query": question,
        "conversation_history": []
    }

    full_answer_parts = []
    sources = []

    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = response.read().decode("utf-8", errors="replace")
                    return {
                        "answer": f"HTTP Error {response.status_code}: {error_text}",
                        "sources": [],
                        "context": f"Failed to retrieve context: {error_text}"
                    }

                current_event = None
                for line in response.iter_lines():
                    if not line:
                        current_event = None
                        continue

                    if line.startswith("event: "):
                        current_event = line[len("event: "):].strip()
                    elif line.startswith("data: "):
                        data_str = line[len("data: "):]

                        if current_event == "token":
                            # Unescape newlines sent over SSE
                            token = data_str.replace("\\n", "\n")
                            full_answer_parts.append(token)
                        elif current_event == "sources":
                            try:
                                sources = json.loads(data_str)
                            except json.JSONDecodeError:
                                sources = []
                        elif current_event == "error":
                            full_answer_parts.append(f"\n[Error: {data_str}]")

    except Exception as exc:
        return {
            "answer": f"Connection Error to RAGnition ({url}): {str(exc)}",
            "sources": [],
            "context": f"Error: {str(exc)}"
        }

    full_answer = "".join(full_answer_parts).strip()
    
    # Format context blocks for the evaluator
    context_text = "\n\n".join(
        f"[Page {s.get('page_number', '?')}] {s.get('snippet', '')}"
        for s in sources
    ) if sources else "No context retrieved."

    return {
        "answer": full_answer,
        "sources": sources,
        "context": context_text
    }
