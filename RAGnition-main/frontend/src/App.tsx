/**
 * App.tsx — top-level component.
 * Manages which view is shown: UploadView or ChatView.
 */
import { useState } from "react";
import { PreLoader } from "./components/PreLoader";
import { UploadView } from "./components/UploadView";
import { ChatView } from "./components/ChatView";
import type { DocumentMeta } from "./types";

export default function App() {
  const [showLoader, setShowLoader] = useState(true);
  const [document, setDocument] = useState<DocumentMeta | null>(null);

  return (
    <>
      {showLoader && (
        <PreLoader onFinished={() => setShowLoader(false)} />
      )}
      <div className={`app-shell ${showLoader ? "" : "app-shell--visible"}`}>
        {document ? (
          <ChatView
            document={document}
            onNewDocument={() => setDocument(null)}
          />
        ) : (
          <UploadView onUploaded={(meta) => setDocument(meta)} />
        )}
      </div>
    </>
  );
}
