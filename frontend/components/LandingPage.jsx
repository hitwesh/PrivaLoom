const valueCards = [
  {
    title: "Authenticated Workspaces",
    copy: "Access is controlled through login, role-based permissions, and stage-level routing for safer multi-client usage.",
  },
  {
    title: "Verified Update Pipeline",
    copy: "Client updates are validated against authenticated identity before robust aggregation and reputation checks.",
  },
  {
    title: "Operator Governance",
    copy: "Admin controls include user lifecycle management, telemetry oversight, and simulation flows for testing decisions.",
  },
];

const flowSteps = [
  {
    step: "01",
    title: "Authenticate and scope session",
    copy: "Each user enters through explicit login or sign-up flow and receives role-scoped access to the workspace.",
  },
  {
    step: "02",
    title: "Process local updates",
    copy: "Client-side processing produces compact update slices while sensitive source data remains local to the user context.",
  },
  {
    step: "03",
    title: "Validate and aggregate",
    copy: "Server validation, reputation filtering, and robust aggregation apply accepted updates to targeted model layers.",
  },
];

const projectFacts = [
  {
    title: "Implemented Now",
    copy: "Auth/RBAC, workspace gating, upload dispatch, backend telemetry, and admin simulation are live.",
  },
  {
    title: "Security Controls",
    copy: "Validation pipeline, outlier checks, and reputation logic actively filter risky or malformed updates.",
  },
  {
    title: "Admin Operations",
    copy: "Account management and simulate-user workflows support practical governance and scenario testing.",
  },
  {
    title: "Next Scope",
    copy: "Model checkpoint persistence, deeper auth hardening, and richer auditability remain top priorities.",
  },
];

const scopeStatus = [
  { label: "Authentication + RBAC", state: "Live" },
  { label: "Upload Validation + Aggregation", state: "Live" },
  { label: "Admin Simulation Controls", state: "Live" },
  { label: "Model Persistence Layer", state: "In progress" },
];

const researchTags = [
  "Privacy-first workflow",
  "Role-based operations",
  "Robust aggregation",
  "Telemetry-driven governance",
];

const researchSnapshot = [
  {
    title: "Session Model",
    copy: "SQLite-backed sessions with role-scoped routing across access, workspace, and admin surfaces.",
  },
  {
    title: "Update Integrity",
    copy: "Authenticated identity is enforced during update validation before aggregation and reputation checks.",
  },
];

const projectSignals = ["Auth", "Validation", "Reputation", "Aggregation"];

export default function LandingPage({ onStart }) {
  return (
    <section className="landing-shell">
      <div className="landing-content">
        <div className="landing-panel card-surface">
          <div className="landing-main">
            <p className="landing-eyebrow">Research Overview</p>
            <h1>Private model improvement for regulated, multi-client teams.</h1>
            <p className="landing-copy">
              PrivaLoom combines local data handling with centralized governance so teams can
              improve shared models while maintaining strict operational boundaries.
            </p>

            <div className="landing-actions">
              <button className="btn-primary" type="button" onClick={onStart}>
                Enter Client Access
              </button>
            </div>

            <div className="landing-metrics">
              <article>
                <h3>Auth + RBAC</h3>
                <p>Role-gated workspace access</p>
              </article>
              <article>
                <h3>Admin Ready</h3>
                <p>User simulation and controls</p>
              </article>
              <article>
                <h3>Validated Path</h3>
                <p>Upload-to-aggregation telemetry loop</p>
              </article>
            </div>

            <div className="landing-snapshot">
              <p className="landing-snapshot-title">Research Snapshot</p>
              <div className="landing-snapshot-grid">
                {researchSnapshot.map((item) => (
                  <article key={item.title} className="landing-snapshot-card">
                    <h4>{item.title}</h4>
                    <p>{item.copy}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>

          <aside className="landing-side">
            <p className="landing-side-title">Current Scope</p>
            <div className="landing-scope-list">
              {scopeStatus.map((item) => (
                <article key={item.label} className="landing-scope-item">
                  <p>{item.label}</p>
                  <span>{item.state}</span>
                </article>
              ))}
            </div>

            <p className="landing-side-title">Platform Highlights</p>
            <div className="landing-card-list">
              {valueCards.map((card) => (
                <article key={card.title} className="landing-value-card">
                  <h4>{card.title}</h4>
                  <p>{card.copy}</p>
                </article>
              ))}
            </div>
          </aside>
        </div>

        <article className="project-article card-surface">
          <p className="project-meta">
            <span>April 2026</span>
            <span>Research Scope</span>
          </p>
          <h2>Validated capabilities for privacy-first model operations</h2>
          <p className="project-lead">
            The current platform supports authenticated access, role-aware operations, and a live
            update-validation-aggregation workflow designed for privacy-sensitive environments.
          </p>

          <div className="project-tag-row">
            {researchTags.map((tag) => (
              <span key={tag} className="project-tag">
                {tag}
              </span>
            ))}
          </div>

          <div className="project-body">
            <div className="project-main-column">
              <div className="project-body-copy">
                <p>
                  Current deployment scope includes login/sign-up access, SQLite-backed session
                  management, admin-only governance surfaces, and authenticated update dispatch.
                </p>
                <p>
                  Security and quality checks are active in the update pipeline through validation,
                  outlier-aware filtering, and reputation-informed aggregation before model updates
                  are applied.
                </p>
              </div>

              <div className="project-facts-grid">
                {projectFacts.map((item) => (
                  <article key={item.title} className="project-fact-card">
                    <h3>{item.title}</h3>
                    <p>{item.copy}</p>
                  </article>
                ))}
              </div>
            </div>

            <div className="project-side-column">
              <ol className="project-flow-list">
                {flowSteps.map((item) => (
                  <li key={item.title} className="project-flow-item">
                    <span className="project-step-index">{item.step}</span>
                    <div>
                      <h3>{item.title}</h3>
                      <p>{item.copy}</p>
                    </div>
                  </li>
                ))}
              </ol>

              <div className="project-side-fill">
                <p className="project-side-fill-title">Operations Rail</p>
                <div className="project-side-signal-grid">
                  {projectSignals.map((item) => (
                    <article key={item} className="project-side-signal">
                      <span className="project-signal-dot" aria-hidden="true" />
                      <p>{item}</p>
                    </article>
                  ))}
                </div>

                <p className="project-side-note">
                  Session is secured, validation checks are active, and aggregation is ready.
                </p>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}
