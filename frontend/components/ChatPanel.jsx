import { useState } from "react";

export default function ChatPanel({ accountName, clientWorkspace, onPromptSubmitted }) {
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState([
    {
      role: "assistant",
      text: `Workspace is live for ${accountName} in ${clientWorkspace}. Share a prompt to test your local model while keeping all context private.`,
    },
  ]);

  const sendMessage = () => {
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }

    onPromptSubmitted?.(trimmed);

    setHistory((prev) => [
      ...prev,
      { role: "user", text: trimmed },
      {
        role: "assistant",
        text: "Received. In a full integration, this message would be processed by your local model endpoint.",
      },
    ]);
    setMessage("");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <section className="chat-shell card-surface">
      <header className="chat-head">
        <div>
          <p className="chat-label">Priva Loom Chat</p>
          <h2>Local Model Conversation</h2>
        </div>
        <span className="chat-status">
          <span className="status-dot" />
          Private session
        </span>
      </header>

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
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message your local model..."
        />
        <button className="chat-send-btn" type="button" onClick={sendMessage}>
          Send
        </button>
      </div>
    </section>
  );
}
