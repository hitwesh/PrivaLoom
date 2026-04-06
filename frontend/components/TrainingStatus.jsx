const statusItems = [
  {
    label: "Model initialized",
    state: "done",
    stateLabel: "Online",
  },
  {
    label: "GPU check complete",
    state: "done",
    stateLabel: "Ready",
  },
  {
    label: "Awaiting training data",
    state: "waiting",
    stateLabel: "Waiting",
  },
];

export default function TrainingStatus() {
  return (
    <section className="panel card-surface">
      <div className="panel-head">
        <h3>Training Status</h3>
        <span className="panel-kicker">Model</span>
      </div>

      <ul className="status-list">
        {statusItems.map((item) => (
          <li key={item.label} className="status-row">
            <span className="status-label">{item.label}</span>
            <span className={`status-pill ${item.state}`}>{item.stateLabel}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
