const fallbackUpdates = [
  {
    time: "--:--",
    tag: "Session",
    text: "Workspace is ready. Activity will appear as you upload documents and send prompts.",
  },
];

export default function UpdateLog({ updates = [] }) {
  const entries = updates.length > 0 ? updates : fallbackUpdates;

  return (
    <section className="panel card-surface">
      <div className="panel-head">
        <h3>Update Log</h3>
        <span className="panel-kicker">Session</span>
      </div>

      <ul className="update-list">
        {entries.map((entry, index) => (
          <li key={`${entry.time}-${entry.text}-${index}`} className="update-row">
            <span className="update-time">{entry.time}</span>
            <p>
              {entry.tag ? <span className="update-tag">{entry.tag}</span> : null}
              {entry.text}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
