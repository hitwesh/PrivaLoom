import { useState } from "react";

export default function ChatPanel() {
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState([]);

  const sendMessage = () => {
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }

    setHistory((prev) => [...prev, `You: ${trimmed}`]);
    setMessage("");
  };

  return (
    <div className="bottom-section">
      <section className="card">
        <h3>Chat Panel</h3>
        <div>
          <input
            type="text"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask a question about your local model"
          />
          <button type="button" onClick={sendMessage}>
            Send
          </button>
        </div>
        <ul>
          {history.length === 0 ? <li>No messages yet</li> : null}
          {history.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
