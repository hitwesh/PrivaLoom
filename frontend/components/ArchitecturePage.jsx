const systemLayers = [
  {
    title: "Access and Identity Layer",
    copy: "Authentication, session tokens, and role checks gate every protected endpoint and workspace surface.",
  },
  {
    title: "Client Processing Node",
    copy: "Sensitive data stays local while the client computes compact update slices for collaborative learning.",
  },
  {
    title: "Validation and Reputation Pipeline",
    copy: "Server-side checks validate structure, bounds, and trust signals before updates are accepted.",
  },
  {
    title: "Robust Aggregation Core",
    copy: "Accepted updates are buffered, filtered, and aggregated using byzantine-aware methods before model application.",
  },
  {
    title: "Operator Workspace",
    copy: "Admin telemetry, account governance, and simulate-user controls provide practical operational oversight.",
  },
];

const flow = [
  "User authenticates and receives a role-scoped session.",
  "Local client computes compact update slices from private context.",
  "Authenticated updates are transmitted with canonical user identity.",
  "Validation, outlier checks, and reputation filtering gate acceptance.",
  "Robust aggregation applies vetted updates to selected model layers.",
  "Workspace telemetry surfaces system health and operator controls.",
];

const scopeTracks = [
  {
    title: "Live in Current Scope",
    copy: "Auth/RBAC, admin account lifecycle, user simulation flow, and protected API paths are implemented.",
  },
  {
    title: "Security in Operation",
    copy: "Validation pipeline, reputation filtering, and security event collection actively influence update handling.",
  },
  {
    title: "Active Next Steps",
    copy: "Model checkpoint persistence, stronger auth hardening, and expanded test depth remain priority workstreams.",
  },
];

export default function ArchitecturePage({ onStart }) {
  return (
    <section className="architecture-shell">
      <article className="architecture-panel card-surface">
        <p className="landing-eyebrow">System Architecture</p>
        <h1>How PrivaLoom coordinates privacy-first model improvement</h1>
        <p className="architecture-copy">
          The platform now combines authenticated workspace access, local update generation,
          validation-first ingestion, and operator governance into one end-to-end learning system.
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

        <div className="architecture-scope-grid">
          {scopeTracks.map((item) => (
            <article key={item.title} className="architecture-scope-card">
              <h3>{item.title}</h3>
              <p>{item.copy}</p>
            </article>
          ))}
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
