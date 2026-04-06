import { useState } from "react";
import UploadPanel from "./components/UploadPanel";
import TrainingStatus from "./components/TrainingStatus";
import UpdateLog from "./components/UpdateLog";
import ChatPanel from "./components/ChatPanel";
import PrivacyBadge from "./components/PrivacyBadge";
import LandingPage from "./components/LandingPage";
import AccessPortal from "./components/AccessPortal";

export default function App() {
  const stageLabels = {
    landing: "Public Landing",
    access: "Client Access",
    workspace: "Training Workspace",
  };

  const [stage, setStage] = useState("landing");
  const [session, setSession] = useState({
    accountName: "",
    clientWorkspace: "",
  });

  const canOpenWorkspace = Boolean(session.accountName && session.clientWorkspace);

  const handleAccessContinue = ({ accountName, clientWorkspace }) => {
    setSession({ accountName, clientWorkspace });
    setStage("workspace");
  };

  const renderStage = () => {
    if (stage === "landing") {
      return <LandingPage onStart={() => setStage("access")} />;
    }

    if (stage === "access") {
      return (
        <AccessPortal
          onBack={() => setStage("landing")}
          onContinue={handleAccessContinue}
        />
      );
    }

    return (
      <div className="app-shell">
        <aside className="workspace-sidebar">
          <section className="brand-block card-surface">
            <p className="eyebrow">Priva Loom</p>
            <h1>Private AI Workspace</h1>
            <p className="brand-copy">
              Multi-client local console with premium controls for secure training,
              update monitoring, and private model chat.
            </p>

            <div className="workspace-meta">
              <div className="workspace-meta-row">
                <span>Account</span>
                <strong>{session.accountName}</strong>
              </div>
              <div className="workspace-meta-row">
                <span>Client Space</span>
                <strong>{session.clientWorkspace}</strong>
              </div>
            </div>

            <button
              className="btn-ghost"
              type="button"
              onClick={() => setStage("access")}
            >
              Switch Account
            </button>
          </section>

          <div className="sidebar-stack">
            <UploadPanel />
            <TrainingStatus />
            <UpdateLog />
          </div>

          <PrivacyBadge />
        </aside>

        <main className="workspace-main">
          <ChatPanel
            accountName={session.accountName}
            clientWorkspace={session.clientWorkspace}
          />
        </main>
      </div>
    );
  };

  return (
    <div className="site-root">
      <header className="site-header">
        <div className="site-header-inner card-surface">
          <button
            className="brand-signature"
            type="button"
            onClick={() => setStage("landing")}
            aria-label="Go to landing page"
          >
            <span className="brand-core">
              <span className="brand-mark" />
              <span className="brand-name">Priva Loom</span>
            </span>
            <span className="brand-tag">Local AI Training Platform</span>
          </button>

          <nav className="site-nav" aria-label="Primary navigation">
            <button
              className={`site-nav-item ${stage === "landing" ? "is-active" : ""}`}
              type="button"
              onClick={() => setStage("landing")}
            >
              Home
            </button>
            <button
              className={`site-nav-item ${stage === "access" ? "is-active" : ""}`}
              type="button"
              onClick={() => setStage("access")}
            >
              Access
            </button>
            <button
              className={`site-nav-item ${stage === "workspace" ? "is-active" : ""}`}
              type="button"
              onClick={() => {
                if (canOpenWorkspace) {
                  setStage("workspace");
                }
              }}
              disabled={!canOpenWorkspace}
              title={canOpenWorkspace ? "Open workspace" : "Complete access page first"}
            >
              Workspace
            </button>
          </nav>

          <div className="site-stage-badge">
            <span className="header-status-dot" />
            <span>{stageLabels[stage]}</span>
          </div>
        </div>
      </header>

      <main className="site-main">{renderStage()}</main>

      <footer className="site-footer">
        <div className="site-footer-inner card-surface">
          <p className="footer-brand">Priva Loom</p>
          <p className="footer-copy">
            Multi-client local model training, private updates, and secure chat workflow.
          </p>
          <p className="footer-meta">Demo Mode</p>
        </div>
      </footer>
    </div>
  );
}