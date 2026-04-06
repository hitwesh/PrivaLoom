const valueCards = [
  {
    title: "Private by Default",
    copy: "Keep sensitive training context on-device and transmit compact learning signals instead of raw datasets.",
  },
  {
    title: "Multi-Client Ready",
    copy: "Separate model lifecycles by client workspace so teams can collaborate without mixing data boundaries.",
  },
  {
    title: "Federated-Style Learning",
    copy: "Aggregate local updates from many users to improve a shared model path without centralizing source data.",
  },
];

const flowSteps = [
  {
    step: "01",
    title: "Local understanding",
    copy: "User text is processed on the client node to generate learning signals close to the data source.",
  },
  {
    step: "02",
    title: "Protected updates",
    copy: "Gradient slices are clipped and noise-controlled before transmission to reduce direct information leakage.",
  },
  {
    step: "03",
    title: "Selective aggregation",
    copy: "Server-side logic buffers and averages updates, then applies them to targeted model layers.",
  },
];

const projectFacts = [
  {
    title: "Current Runtime",
    copy: "DistilGPT2 local bootstrap, FastAPI endpoints (/chat, /send-update), and client update simulation are implemented.",
  },
  {
    title: "Privacy Posture",
    copy: "Data locality is the goal. This prototype uses compact updates and differential privacy controls, while hardening is still in progress.",
  },
  {
    title: "Roadmap Direction",
    copy: "Next priorities include secure aggregation, stronger endpoint security, model persistence, and test automation.",
  },
];

export default function LandingPage({ onStart }) {
  return (
    <section className="landing-shell">
      <div className="landing-content">
        <div className="landing-panel card-surface">
          <div className="landing-main">
            <p className="landing-eyebrow">PrivaLoom</p>
            <h1>Build private AI models with a professional multi-client workflow.</h1>
            <p className="landing-copy">
              A local training platform for teams that need privacy-aware model improvement,
              structured collaboration, and transparent operational controls.
            </p>

            <div className="landing-actions">
              <button className="btn-primary" type="button" onClick={onStart}>
                Enter Client Access
              </button>
            </div>

            <div className="landing-metrics">
              <article>
                <h3>100%</h3>
                <p>Local processing control</p>
              </article>
              <article>
                <h3>Multi-Client</h3>
                <p>Workspace separation support</p>
              </article>
              <article>
                <h3>Prototype+</h3>
                <p>Production-aware architecture direction</p>
              </article>
            </div>
          </div>

          <aside className="landing-side">
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
            <span>Product Architecture</span>
          </p>
          <h2>How PrivaLoom improves language models in sensitive environments</h2>
          <p className="project-lead">
            PrivaLoom is a privacy-first distributed learning framework. Instead of centralizing raw
            user data, it keeps learning close to the user and exchanges compact model-update
            signals across the network.
          </p>

          <div className="project-actions">
            <button className="btn-primary" type="button" onClick={onStart}>
              Try Workspace Access
            </button>
            <button className="btn-ghost" type="button" onClick={onStart}>
              View Client Flow
            </button>
          </div>

          <div className="project-utility-row">
            <p>Read architecture brief | 4 min</p>
            <button className="project-share-btn" type="button">
              Share summary
            </button>
          </div>

          <div className="project-body">
            <div className="project-body-copy">
              <p>
                The current codebase already includes local model bootstrap, a FastAPI server, a
                client update loop, in-memory aggregation, and selective layer updates. This means
                teams can demonstrate privacy-aware collaboration with a working end-to-end flow.
              </p>
              <p>
                Differential privacy controls are available in the client path through configurable
                clipping and noise parameters. The system is intentionally transparent about its
                current maturity and roadmap, with secure aggregation and stronger security layers
                planned next.
              </p>
              <p>
                The UI mirrors that architecture: landing and access stages for multi-client
                onboarding, then a focused workspace for private chat, dataset intake, status
                monitoring, and update visibility.
              </p>
            </div>

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
          </div>

          <div className="project-facts-grid">
            {projectFacts.map((item) => (
              <article key={item.title} className="project-fact-card">
                <h3>{item.title}</h3>
                <p>{item.copy}</p>
              </article>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
