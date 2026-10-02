# Document AI Assistant

A full-stack RAG (Retrieval-Augmented Generation) assistant that lets you upload a PDF or text document, then ask questions about it in a multi-turn conversation. Every answer is **grounded** in the document and includes **page-level citations** so you can verify where each fact came from.

---

## Tech Stack

| Layer                 | Technology                                                  |
| --------------------- | ----------------------------------------------------------- |
| **Frontend**    | React 18 + Vite + TypeScript                                |
| **Backend**     | FastAPI + Uvicorn                                           |
| **Vector DB**   | ChromaDB (persistent, per-document)                         |
| **Embeddings**  | Google Generative AI Embeddings (`gemini-embedding-2`)    |
| **LLM**         | Gemini 1.5 Flash via LangChain (`ChatGoogleGenerativeAI`) |
| **PDF parsing** | PyPDFLoader (LangChain community)                           |
| **Streaming**   | Server-Sent Events (SSE) over`fetch` ReadableStream       |

---

## Project Structure

```
PDF-Analyzer-GenAI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── api/
│   │   │   ├── upload.py        # POST /api/upload
│   │   │   └── chat.py          # POST /api/chat  (SSE stream)
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings, all tunable knobs
│   │   │   ├── document_store.py # PDF → chunks → embeddings → Chroma
│   │   │   └── rag_chain.py     # retrieval + prompt + LLM + SSE events
│   │   └── models/
│   │       └── schemas.py       # Pydantic v2 request/response models
│   ├── storage/                 # gitignored: uploaded files + chroma dirs
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/client.ts        # fetch-based upload + SSE stream client
│       ├── hooks/useChat.ts     # chat state, streaming, history management
│       ├── components/
│       │   ├── UploadView.tsx   # drag-and-drop upload
│       │   ├── ChatView.tsx     # message list + input form
│       │   ├── MessageBubble.tsx
│       │   └── SourcesPanel.tsx # expandable citations panel
│       ├── types/index.ts       # shared TypeScript types
│       ├── App.tsx
│       └── index.css
└── README.md
```

---

## Setup & Running

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Gemini API key → [Get one at Google AI Studio](https://aistudio.google.com)

---

### Backend

```bash
# 1. Create and activate a virtual environment
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env file
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS

# Edit .env and set your GOOGLE_API_KEY
# GOOGLE_API_KEY=your_key_here

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at **http://localhost:8000**.
Interactive Swagger docs: **http://localhost:8000/docs**

---

### Frontend

```bash
cd frontend
npm install        # only needed once
npm run dev
```

The React app will be available at **http://localhost:5173**.

> The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`,
> so no CORS configuration is needed during local development.

---

## How Chunking & Retrieval Work

### 1. Document Loading (per-page)

`PyPDFLoader` loads the PDF and returns **one `Document` object per page**.
Each Document carries `metadata["page"]` (0-indexed) set by the loader.
We immediately add `metadata["source_page"] = page + 1` (1-indexed, for display).

### 2. Chunking (page metadata preserved)

Each page Document is split with `RecursiveCharacterTextSplitter`:

| Parameter         | Value                            | Rationale                                                                     |
| ----------------- | -------------------------------- | ----------------------------------------------------------------------------- |
| `chunk_size`    | 800 chars ≈ ~200 tokens         | Small enough for precise retrieval; large enough to hold a coherent paragraph |
| `chunk_overlap` | 150 chars                        | Prevents sentences that span chunk boundaries from being lost                 |
| `separators`    | `["\n\n", "\n", ".", " ", ""]` | Tries to split on natural paragraph/sentence boundaries first                 |

`split_documents()` **automatically propagates parent metadata** to all child chunks,
so every chunk knows which page it came from.
We additionally inject `chunk_id = "{document_id}-p{page}-c{index}"` into each chunk's metadata.

### 3. Embedding & Storage

Chunks are embedded with `gemini-embedding-2` and stored in a **dedicated ChromaDB collection**
named `doc_{document_id}`, persisted at `storage/chroma/{document_id}/`.
Each document upload creates a **new, isolated collection** — existing documents are never overwritten.

### 4. Retrieval

At chat time, the user's query is embedded and a **cosine similarity search** over the document's
Chroma collection returns the top **k = 5** most relevant chunks (configurable via `TOP_K` env var).

### 5. Citation Construction

The retrieved chunks already carry `source_page` and `chunk_id` in their metadata.
After the LLM generates its answer, we extract these fields and return them as a
`sources` array in the final SSE event:

```json
[
  { "chunk_id": "abc-p3-c7", "page_number": 3, "snippet": "The mitochondria is..." },
  ...
]
```

The frontend renders these in an expandable "View sources" panel beneath each assistant message.

---

## API Reference

### `POST /api/upload`

Upload a PDF or TXT file (multipart form data).

**Response:**

```json
{
  "document_id": "550e8400-e29b-...",
  "filename": "paper.pdf",
  "num_pages": 12,
  "num_chunks": 47
}
```

### `POST /api/chat`

Stream a RAG-grounded answer as SSE.

**Request body:**

```json
{
  "document_id": "550e8400-e29b-...",
  "query": "What is the main conclusion?",
  "conversation_history": [
    { "role": "user", "content": "What is this paper about?" },
    { "role": "assistant", "content": "It is about..." }
  ]
}
```

**SSE event stream:**

```
event: token
data: The main conclusion

event: token
data:  is that...

event: sources
data: [{"chunk_id":"...","page_number":8,"snippet":"..."}]

event: done
data: [DONE]
```

---

## Environment Variables

| Variable             | Default                       | Description                              |
| -------------------- | ----------------------------- | ---------------------------------------- |
| `GOOGLE_API_KEY`   | _(required)_                | Google Gemini API key                    |
| `GEMINI_MODEL`     | `models/gemini-2.5-flash`   | LLM model name                           |
| `EMBEDDING_MODEL`  | `models/gemini-embedding-2` | Embedding model name                     |
| `CHUNK_SIZE`       | `800`                       | Characters per chunk                     |
| `CHUNK_OVERLAP`    | `150`                       | Overlap between adjacent chunks          |
| `TOP_K`            | `5`                         | Number of chunks retrieved per query     |
| `STORAGE_DIR`      | `./storage`                 | Root directory for uploads + Chroma data |
| `MAX_FILE_SIZE_MB` | `50`                        | Maximum upload size                      |
| `CORS_ORIGINS`     | `["http://localhost:5173"]` | Allowed frontend origins                 |

---

## Known Limitations

| Limitation                               | Notes                                                                                                                                     |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **No authentication**              | Any user can access any`document_id` if they know it. Suitable for single-user/local use only.                                          |
| **In-memory conversation history** | History is maintained in React state and resent by the client each turn. Refreshing the page loses the conversation.                      |
| **No document management UI**      | There's no list/delete UI for uploaded documents. Chroma collections persist on disk indefinitely.                                        |
| **Single-file upload**             | Only one document per session. Multi-document or cross-document Q&A is not supported.                                                     |
| **Gemini rate limits**             | Heavy use may hit Google AI API rate limits; no retry logic is implemented beyond LangChain defaults.                                     |
| **No OCR**                         | Scanned PDFs (images only, no embedded text) will produce empty pages. Use text-layer PDFs.                                               |
| **Page number accuracy**           | Page numbers reflect the PDF's page order as parsed. Scanned PDFs, headers, or non-standard layouts may produce off-by-one discrepancies. |
