/**
 * API client for the FastAPI backend.
 *
 * uploadDocument — multipart POST to /api/upload
 * streamChat     — POST to /api/chat, parses SSE manually via fetch ReadableStream
 *                  (EventSource doesn't support POST bodies)
 */
import type { ChatRequest, SourceChunk, UploadResponse } from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE_URL}/api/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload failed");
  }

  return res.json() as Promise<UploadResponse>;
}

// ---------------------------------------------------------------------------
// Chat (SSE stream)
// ---------------------------------------------------------------------------

export interface StreamChatCallbacks {
  onToken: (token: string) => void;
  onSources: (sources: SourceChunk[]) => void;
  onDone: () => void;
  onError: (msg: string) => void;
}

/**
 * Sends a chat request and streams the response via SSE.
 * Returns an AbortController so the caller can cancel the stream.
 */
export function streamChat(
  request: ChatRequest,
  callbacks: StreamChatCallbacks
): AbortController {
  const controller = new AbortController();

  (async () => {
    let res: Response;
    try {
      res = await fetch(`${BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: controller.signal,
      });
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") return;
      callbacks.onError("Network error — could not reach the backend.");
      return;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      callbacks.onError(err.detail ?? "Chat request failed");
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      callbacks.onError("No response body from server.");
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE messages are separated by double newlines
        const parts = buffer.split("\n\n");
        // The last element may be an incomplete message — keep it in the buffer
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const lines = part.trim().split("\n");
          let eventType = "message";
          let data = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              data = line.slice(6);
            }
          }

          if (!data) continue;

          switch (eventType) {
            case "token":
              // Unescape newlines that the server escaped
              callbacks.onToken(data.replace(/\\n/g, "\n"));
              break;
            case "sources":
              try {
                callbacks.onSources(JSON.parse(data) as SourceChunk[]);
              } catch {
                console.warn("Failed to parse sources payload:", data);
              }
              break;
            case "done":
              callbacks.onDone();
              break;
            case "error":
              try {
                const parsed = JSON.parse(data);
                callbacks.onError(parsed.detail ?? "Unknown stream error");
              } catch {
                callbacks.onError(data);
              }
              break;
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error).name !== "AbortError") {
        callbacks.onError("Stream interrupted unexpectedly.");
      }
    } finally {
      reader.releaseLock();
    }
  })();

  return controller;
}
