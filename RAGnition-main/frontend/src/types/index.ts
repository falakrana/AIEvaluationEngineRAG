/**
 * Shared TypeScript types for the Document AI Assistant frontend.
 */

// ---------------------------------------------------------------------------
// API response types
// ---------------------------------------------------------------------------

export interface UploadResponse {
  document_id: string;
  filename: string;
  num_pages: number;
  num_chunks: number;
}

export interface SourceChunk {
  chunk_id: string;
  page_number: number;
  snippet: string;
}

export interface ChatRequest {
  document_id: string;
  query: string;
  conversation_history: Turn[];
}

export interface Turn {
  role: "user" | "assistant";
  content: string;
}

// ---------------------------------------------------------------------------
// UI state types
// ---------------------------------------------------------------------------

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** Only present on assistant messages after streaming completes */
  sources?: SourceChunk[];
  /** True while the assistant is still streaming this message */
  isStreaming?: boolean;
}

export interface DocumentMeta {
  document_id: string;
  filename: string;
  num_pages: number;
  num_chunks: number;
}
