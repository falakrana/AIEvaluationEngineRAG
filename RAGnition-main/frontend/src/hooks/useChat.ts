/**
 * useChat — custom hook encapsulating all chat state and logic.
 *
 * Manages:
 *   - messages array (both user and assistant turns)
 *   - conversation_history for multi-turn context (sent to backend each turn)
 *   - streaming state (isStreaming, current streaming message id)
 *   - send / cancel actions
 */
import { useCallback, useRef, useState } from "react";
import { streamChat } from "../api/client";
import type { DocumentMeta, Message, SourceChunk, Turn } from "../types";

function uid(): string {
  return Math.random().toString(36).slice(2, 11);
}

export function useChat(document: DocumentMeta) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Conversation history maintained in sync with messages
  const historyRef = useRef<Turn[]>([]);

  const sendMessage = useCallback(
    (query: string) => {
      if (isStreaming || !query.trim()) return;

      const userMsg: Message = { id: uid(), role: "user", content: query };
      const assistantId = uid();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
        sources: undefined,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      // Snapshot history at the time of the request
      const historySnapshot: Turn[] = [...historyRef.current];

      const controller = streamChat(
        {
          document_id: document.document_id,
          query,
          conversation_history: historySnapshot,
        },
        {
          onToken(token) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },

          onSources(sources: SourceChunk[]) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, sources } : m
              )
            );
          },

          onDone() {
            setIsStreaming(false);
            abortRef.current = null;

            // Capture final assistant content and update history
            setMessages((prev) => {
              const assistantFinal = prev.find((m) => m.id === assistantId);
              if (assistantFinal) {
                historyRef.current = [
                  ...historySnapshot,
                  { role: "user", content: query },
                  { role: "assistant", content: assistantFinal.content },
                ];
              }
              return prev.map((m) =>
                m.id === assistantId ? { ...m, isStreaming: false } : m
              );
            });
          },

          onError(msg: string) {
            setIsStreaming(false);
            abortRef.current = null;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content: `⚠️ Error: ${msg}`,
                      isStreaming: false,
                    }
                  : m
              )
            );
          },
        }
      );

      abortRef.current = controller;
    },
    [isStreaming, document.document_id]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m) =>
        m.isStreaming ? { ...m, isStreaming: false, content: m.content + " _(cancelled)_" } : m
      )
    );
  }, []);

  const clearChat = useCallback(() => {
    historyRef.current = [];
    setMessages([]);
  }, []);

  return { messages, isStreaming, sendMessage, cancelStream, clearChat };
}
