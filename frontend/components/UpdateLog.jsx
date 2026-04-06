const updates = [
  {
    time: "19:44",
    text: "Workspace shell upgraded to a premium grayscale interface.",
  },
  {
    time: "19:41",
    text: "Missing dashboard components restored and wired into App.",
  },
  {
    time: "19:39",
    text: "Vite entry path corrected and startup flow stabilized.",
  },
];

export default function UpdateLog() {
  return (
    <section className="panel card-surface">
      <div className="panel-head">
        <h3>Update Log</h3>
        <span className="panel-kicker">Live</span>
      </div>

      <ul className="update-list">
        {updates.map((entry) => (
          <li key={`${entry.time}-${entry.text}`} className="update-row">
            <span className="update-time">{entry.time}</span>
            <p>{entry.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
