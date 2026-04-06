const systemLayers = [
  {
    title: "Client Learning Node",
    copy: "Sensitive user data is processed locally. The client computes compact learning signals close to the data source.",
  },
  {
    title: "Privacy Guardrail",
    copy: "Updates are prepared with clipping and controlled noise before being sent to the aggregation channel.",
  },
  {
    title: "Aggregation Service",
    copy: "The server receives update slices from multiple clients and applies averaged updates to selected model layers.",
  },
  {
    title: "Workspace Control",
    copy: "Teams monitor document intake, model status, and activity signals through an operator-focused UI.",
  },
];

const flow = [
  "User data is processed on the local client.",
  "The model computes compact update slices.",
  "Protected updates are sent to the server.",
  "Server aggregates updates across clients.",
  "Selected model layers receive averaged improvements.",
];

export default function ArchitecturePage({ onStart }) {
  return (
    <section className="architecture-shell">
      <article className="architecture-panel card-surface">
        <p className="landing-eyebrow">System Architecture</p>
        <h1>How PrivaLoom coordinates privacy-first model improvement</h1>
        <p className="architecture-copy">
          PrivaLoom combines local client learning with centralized aggregation so teams can improve
          shared language models while keeping sensitive source data within each user environment.
        </p>

        <div className="architecture-grid">
          {systemLayers.map((layer) => (
            <article key={layer.title} className="architecture-card">
              <h3>{layer.title}</h3>
              <p>{layer.copy}</p>
            </article>
          ))}
        </div>

        <div className="architecture-flow card-surface">
          <p className="architecture-flow-title">Learning Flow</p>
          <ol>
            {flow.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>

        <div className="architecture-actions">
          <button className="btn-primary" type="button" onClick={onStart}>
            Open Client Access
          </button>
        </div>
      </article>
    </section>
  );
}
