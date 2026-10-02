/**
 * UploadView — drag-and-drop PDF/TXT uploader.
 * Shows upload progress and transitions to the chat view on success.
 */
import { useCallback, useRef, useState } from "react";
import { uploadDocument } from "../api/client";
import type { DocumentMeta } from "../types";

interface Props {
  onUploaded: (meta: DocumentMeta) => void;
}

type UploadState = "idle" | "dragging" | "uploading" | "error";

export function UploadView({ onUploaded }: Props) {
  const [state, setState] = useState<UploadState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      const allowed = ["application/pdf", "text/plain"];
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!allowed.includes(file.type) && ext !== "pdf" && ext !== "txt") {
        setState("error");
        setErrorMsg("Only PDF and TXT files are supported.");
        return;
      }

      setState("uploading");
      setErrorMsg("");

      // Fake progress animation while the real request is in flight
      let fakeProgress = 0;
      const interval = setInterval(() => {
        fakeProgress = Math.min(fakeProgress + 8, 85);
        setProgress(fakeProgress);
      }, 200);

      try {
        const result = await uploadDocument(file);
        clearInterval(interval);
        setProgress(100);
        setTimeout(() => {
          onUploaded({
            document_id: result.document_id,
            filename: result.filename,
            num_pages: result.num_pages,
            num_chunks: result.num_chunks,
          });
        }, 400);
      } catch (err: unknown) {
        clearInterval(interval);
        setState("error");
        setErrorMsg((err as Error).message ?? "Upload failed. Please try again.");
        setProgress(0);
      }
    },
    [onUploaded]
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setState("idle");
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setState("dragging");
  };

  const onDragLeave = () => setState("idle");

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="upload-view">
      <div className="upload-header">
        <div className="logo-mark">◈</div>
        <h1 className="app-title">Document AI Assistant</h1>
        <p className="app-subtitle">
          Upload a PDF or text file to start a grounded conversation with your document.
        </p>
      </div>

      <div
        className={`drop-zone ${state === "dragging" ? "drop-zone--active" : ""} ${state === "uploading" ? "drop-zone--uploading" : ""} ${state === "error" ? "drop-zone--error" : ""}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => state !== "uploading" && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload document"
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          className="file-input-hidden"
          onChange={onInputChange}
          id="file-upload-input"
        />

        {state === "uploading" ? (
          <div className="upload-progress-container">
            <div className="upload-spinner" aria-label="Uploading..." />
            <p className="upload-status-text">Processing document…</p>
            <div className="progress-bar-track">
              <div
                className="progress-bar-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="progress-pct">{progress}%</p>
          </div>
        ) : (
          <div className="drop-zone-content">
            <div className="drop-icon" aria-hidden="true">📄</div>
            <p className="drop-label">
              {state === "dragging"
                ? "Drop it here!"
                : "Drag & drop your file here"}
            </p>
            <p className="drop-sublabel">or click to browse</p>
            <p className="drop-hint">PDF · TXT · up to 50 MB</p>
          </div>
        )}
      </div>

      {state === "error" && (
        <div className="upload-error" role="alert">
          <span className="error-icon">⚠</span> {errorMsg}
          <button
            className="error-retry"
            onClick={() => setState("idle")}
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
