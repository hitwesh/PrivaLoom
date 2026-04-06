import { useState } from "react";

export default function ChatPanel({
  accountName,
  clientWorkspace,
  onPromptSubmitted,
  backendError,
  statusSummary,
}) {
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [history, setHistory] = useState([
    {
      role: "assistant",
      text: `Workspace is live for ${accountName} in ${clientWorkspace}. Share a prompt to test your local model while keeping all context private.`,
    },
  ]);

  const sendMessage = async () => {
    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }

    setHistory((prev) => [
      ...prev,
      { role: "user", text: trimmed },
    ]);
    setMessage("");

    try {
      setIsSending(true);
      const responseText = await onPromptSubmitted?.(trimmed);
      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          text: responseText || "No model response returned.",
        },
      ]);
    } catch (error) {
      const text = error instanceof Error ? error.message : "Request failed.";
      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Chat request failed: ${text}`,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const bufferCount = statusSummary?.current_buffer_size ?? 0;
  const threshold = statusSummary?.threshold ?? "?";

  return (
    <section className="chat-shell card-surface">
      <header className="chat-head">
        <div>
          <p className="chat-label">Priva Loom Chat</p>
          <h2>Local Model Conversation</h2>
        </div>
        <span className="chat-status">
          <span className="status-dot" />
          {backendError ? "Backend issue" : `Buffer ${bufferCount}/${threshold}`}
        </span>
      </header>

      {backendError ? <p className="chat-error-banner">{backendError}</p> : null}

      <div className="chat-scroll">
        {history.map((item, index) => (
          <article key={`${item.role}-${index}`} className={`message message-${item.role}`}>
            <small className="message-role">
              {item.role === "assistant" ? "Assistant" : "You"}
            </small>
            <p>{item.text}</p>
          </article>
        ))}
      </div>

      <div className="chat-input-row">
        <input
          className="chat-input"
          type="text"
          value={message}
          disabled={isSending}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message your local model..."
        />
        <button className="chat-send-btn" type="button" onClick={sendMessage} disabled={isSending}>
          {isSending ? "Sending..." : "Send"}
        </button>
      </div>
    </section>
  );
}
