/**
 * SourcesPanel — expandable accordion showing citation chunks
 * that grounded the assistant's answer.
 */
import { useState } from "react";
import type { SourceChunk } from "../types";

interface Props {
  sources: SourceChunk[];
}

export function SourcesPanel({ sources }: Props) {
  const [open, setOpen] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="sources-panel">
      <button
        className="sources-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="sources-icon">{open ? "▾" : "▸"}</span>
        View sources ({sources.length} chunk{sources.length !== 1 ? "s" : ""})
      </button>

      {open && (
        <ul className="sources-list">
          {sources.map((src) => (
            <li key={src.chunk_id} className="source-item">
              <span className="source-page">Page {src.page_number}</span>
              <p className="source-snippet">{src.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
