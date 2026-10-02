/**
 * MessageBubble — renders a single chat message (user or assistant).
 * Assistant messages include a streaming cursor and the SourcesPanel.
 */
import type { Message } from "../types";
import { SourcesPanel } from "./SourcesPanel";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "message-row--user" : "message-row--assistant"}`}>
      <div className={`bubble ${isUser ? "bubble--user" : "bubble--assistant"}`}>
        <div className="bubble-role">{isUser ? "You" : "Assistant"}</div>
        <div className="bubble-content">
          {/* Render content, preserving newlines */}
          {message.content.split("\n").map((line, i) => (
            <span key={i}>
              {line}
              {i < message.content.split("\n").length - 1 && <br />}
            </span>
          ))}
          {message.isStreaming && <span className="streaming-cursor" aria-hidden="true">▋</span>}
        </div>

        {/* Sources panel — only on completed assistant messages */}
        {!isUser && !message.isStreaming && message.sources && (
          <SourcesPanel sources={message.sources} />
        )}
      </div>
    </div>
  );
}
