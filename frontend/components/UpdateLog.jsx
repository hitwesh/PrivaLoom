const updates = [
  "System ready",
  "Frontend components restored",
  "Waiting for user action",
];

export default function UpdateLog() {
  return (
    <section className="card">
      <h3>Update Log</h3>
      <ul>
        {updates.map((entry) => (
          <li key={entry}>{entry}</li>
        ))}
      </ul>
    </section>
  );
}
