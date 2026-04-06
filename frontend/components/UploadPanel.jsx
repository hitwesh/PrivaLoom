import { useEffect, useMemo, useRef, useState } from "react";

const buildFileId = (file) => `${file.name}-${file.size}-${file.lastModified}`;

const formatFileSize = (size) => {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  return `${Math.max(1, Math.round(size / 1024))} KB`;
};

export default function UploadPanel({ onDocumentChange, onSendUpdates }) {
  const [files, setFiles] = useState([]);
  const [selectionTabOpen, setSelectionTabOpen] = useState(false);
  const [sendMessage, setSendMessage] = useState("");
  const [sendError, setSendError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const filesRef = useRef([]);

  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  useEffect(
    () => () => {
      filesRef.current.forEach((entry) => {
        URL.revokeObjectURL(entry.previewUrl);
      });
    },
    []
  );

  const activeFiles = useMemo(
    () => files.filter((entry) => entry.isSelected),
    [files]
  );

  const addFiles = (incomingFiles) => {
    const candidates = Array.from(incomingFiles ?? []);
    if (!candidates.length) {
      return;
    }

    setSendMessage("");
    setSendError("");

    const existingIds = new Set(filesRef.current.map((entry) => entry.id));
    const additions = [];

    candidates.forEach((file) => {
      const id = buildFileId(file);
      if (existingIds.has(id)) {
        return;
      }

      existingIds.add(id);
      additions.push({
        id,
        file,
        previewUrl: URL.createObjectURL(file),
        isSelected: true,
      });
    });

    if (!additions.length) {
      setSelectionTabOpen(true);
      return;
    }

    setFiles((previous) => [...previous, ...additions]);
    additions.forEach((entry) => {
      onDocumentChange?.({
        fileName: entry.file.name,
        fileSize: entry.file.size,
        fileType: entry.file.type || "unknown",
      });
    });
    setSelectionTabOpen(true);
  };

  const handleFileChange = (event) => {
    addFiles(event.target.files);
    event.target.value = "";
  };

  const handleToggleSelected = (id) => {
    setFiles((previous) =>
      previous.map((entry) =>
        entry.id === id ? { ...entry, isSelected: !entry.isSelected } : entry
      )
    );
    setSendMessage("");
    setSendError("");
  };

  const handleSelectAll = (isSelected) => {
    setFiles((previous) => previous.map((entry) => ({ ...entry, isSelected })));
    setSendMessage("");
    setSendError("");
  };

  const handleRemoveFile = (id) => {
    setFiles((previous) => {
      const target = previous.find((entry) => entry.id === id);
      if (target) {
        URL.revokeObjectURL(target.previewUrl);
      }

      return previous.filter((entry) => entry.id !== id);
    });
    setSendMessage("");
    setSendError("");
  };

  const handleOpenFile = (entry) => {
    const popup = window.open(entry.previewUrl, "_blank", "noopener,noreferrer");
    if (!popup) {
      setSendError("Pop-up blocked. Allow pop-ups to preview files in a new tab.");
    }
  };

  const handleSendUpdates = async () => {
    if (!activeFiles.length || isSending) {
      return;
    }

    setIsSending(true);
    setSendMessage("");
    setSendError("");

    try {
      const payload = activeFiles.map((entry) => ({
        file: entry.file,
        fileName: entry.file.name,
        fileSize: entry.file.size,
        fileType: entry.file.type || "unknown",
        lastModified: entry.file.lastModified,
      }));

      const result = await Promise.resolve(onSendUpdates?.({ files: payload }));

      if (result?.status === "accepted") {
        setSendMessage(
          `Update accepted. Buffer count: ${result.buffer_count ?? 0}.`
        );
      } else if (result?.status === "rejected") {
        const reason = result.reason || "validation_failed";
        const details = Array.isArray(result.details) && result.details.length
          ? ` (${result.details.join("; ")})`
          : "";
        setSendError(`Update rejected: ${reason}${details}`);
      } else if (result?.status === "error") {
        setSendError(`Server error: ${result.reason || "unknown"}`);
      } else {
        setSendMessage(
          `${payload.length} file${payload.length > 1 ? "s" : ""} sent for processing.`
        );
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setSendError(`Unable to send updates right now: ${message}`);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <section className="panel card-surface">
      <div className="panel-head">
        <h3>Dataset Intake</h3>
        <span className="panel-kicker">Secure</span>
      </div>

      <label className="file-picker">
        <span>{files.length ? "Add more dataset files" : "Select dataset files"}</span>
        <input type="file" multiple onChange={handleFileChange} />
      </label>

      <div className="upload-controls">
        <button
          className="upload-manage-btn"
          type="button"
          disabled={!files.length}
          onClick={() => setSelectionTabOpen((previous) => !previous)}
        >
          {selectionTabOpen ? "Hide selection tab" : "Open selection tab"}
        </button>
        <span className="upload-summary">
          {activeFiles.length} selected / {files.length} total
        </span>
      </div>

      {files.length && selectionTabOpen ? (
        <div className="dataset-tab">
          <div className="dataset-tab-head">
            <p>Selection tab</p>
            <div className="dataset-tab-actions">
              <button type="button" onClick={() => handleSelectAll(true)}>
                Select all
              </button>
              <button type="button" onClick={() => handleSelectAll(false)}>
                Deselect all
              </button>
            </div>
          </div>

          <ul className="dataset-file-list">
            {files.map((entry) => (
              <li key={entry.id} className="dataset-file-row">
                <label className="dataset-check">
                  <input
                    type="checkbox"
                    checked={entry.isSelected}
                    onChange={() => handleToggleSelected(entry.id)}
                  />
                  <span>{entry.isSelected ? "Selected" : "Deselected"}</span>
                </label>

                <button
                  className="dataset-file-link"
                  type="button"
                  title="Open file preview in a new tab"
                  onClick={() => handleOpenFile(entry)}
                >
                  {entry.file.name}
                </button>

                <span className="dataset-file-size">{formatFileSize(entry.file.size)}</span>

                <button
                  className="dataset-remove-btn"
                  type="button"
                  onClick={() => handleRemoveFile(entry.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="upload-send-row">
        <button
          className="send-update-btn"
          type="button"
          disabled={isSending || activeFiles.length === 0}
          onClick={handleSendUpdates}
        >
          {isSending ? "Sending..." : "Send updates"}
        </button>
      </div>

      <p className="muted-text">
        {files.length
          ? "Click a file name to preview it in a new tab before sending updates."
          : "CSV, JSONL, TXT, and PDF files are accepted for local training."}
      </p>

      {sendMessage ? <p className="upload-feedback success">{sendMessage}</p> : null}
      {sendError ? <p className="upload-feedback error">{sendError}</p> : null}
    </section>
  );
}
