const valueCards = [
  {
    title: "Private by Default",
    copy: "All training and prompt interactions are processed locally with no external data egress.",
  },
  {
    title: "Multi-Client Ready",
    copy: "Segment teams by client workspace and keep each model lifecycle clearly separated.",
  },
  {
    title: "Executive-Grade UX",
    copy: "A focused command center designed for premium operations and high-visibility demos.",
  },
];

export default function LandingPage({ onStart }) {
  return (
    <section className="landing-shell">
      <div className="landing-panel card-surface">
        <div className="landing-main">
          <p className="landing-eyebrow">Priva Loom</p>
          <h1>Build private AI models with a premium multi-client workflow.</h1>
          <p className="landing-copy">
            A professional local training platform for modern teams that need strong privacy,
            structured collaboration, and polished operations.
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
              <h3>Premium</h3>
              <p>Executive-ready interface quality</p>
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
    </section>
  );
}
