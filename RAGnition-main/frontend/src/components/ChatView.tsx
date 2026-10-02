/**
 * ChatView — the main chat interface after a document has been uploaded.
 * Renders the message list, streams tokens, and handles the input form.
 */
import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import type { DocumentMeta } from "../types";

interface Props {
  document: DocumentMeta;
  onNewDocument: () => void;
}

export function ChatView({ document, onNewDocument }: Props) {
  const { messages, isStreaming, sendMessage, cancelStream, clearChat } =
    useChat(document);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as new tokens arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput("");
    sendMessage(q);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <div className="chat-layout">
      {/* ── Sidebar ───────────────────────────────────────────────── */}
      <aside className="chat-sidebar">
        <div className="sidebar-logo">◈</div>
        <div className="doc-info">
          <p className="doc-filename" title={document.filename}>
            {document.filename}
          </p>
          <p className="doc-meta">
            {document.num_pages} page{document.num_pages !== 1 ? "s" : ""}
            &nbsp;·&nbsp;
            {document.num_chunks} chunks
          </p>
        </div>

        <div className="sidebar-actions">
          <button
            className="sidebar-btn"
            onClick={clearChat}
            title="Clear conversation"
          >
            🗑 Clear chat
          </button>
          <button
            className="sidebar-btn sidebar-btn--new"
            onClick={onNewDocument}
            title="Upload a new document"
          >
            ＋ New document
          </button>
        </div>
      </aside>

      {/* ── Main area ─────────────────────────────────────────────── */}
      <main className="chat-main">
        <div className="messages-container" role="log" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <p className="empty-title">Ask anything about</p>
              <p className="empty-doc">{document.filename}</p>
              <p className="empty-hint">
                Answers are grounded in the document and include page citations.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {/* ── Input form ────────────────────────────────────────── */}
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <textarea
            id="chat-query-input"
            className="chat-textarea"
            placeholder="Ask a question about your document… (Enter to send, Shift+Enter for newline)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={isStreaming}
            aria-label="Chat input"
          />
          <div className="input-actions">
            {isStreaming ? (
              <button
                type="button"
                className="btn btn--stop"
                onClick={cancelStream}
                id="stop-stream-btn"
              >
                ⏹ Stop
              </button>
            ) : (
              <button
                type="submit"
                className="btn btn--send"
                disabled={!input.trim()}
                id="send-message-btn"
              >
                Send ↑
              </button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
