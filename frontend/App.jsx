import { useState } from "react";
import UploadPanel from "./components/UploadPanel";
import TrainingStatus from "./components/TrainingStatus";
import UpdateLog from "./components/UpdateLog";
import ChatPanel from "./components/ChatPanel";
import PrivacyBadge from "./components/PrivacyBadge";
import LandingPage from "./components/LandingPage";
import AccessPortal from "./components/AccessPortal";

const MAX_LOG_ITEMS = 8;

const footerColumns = [
  {
    title: "Platform",
    links: ["Private Chat Workspace", "Dataset Intake", "Training Status", "Update Log"],
  },
  {
    title: "Privacy",
    links: ["Local Processing", "Gradient Clipping", "Noise Controls", "Trust Boundaries"],
  },
  {
    title: "Architecture",
    links: ["Client Node", "FastAPI Server", "Aggregation Flow", "Selective Updates"],
  },
  {
    title: "Resources",
    links: ["Project Bible", "Architecture Notes", "Roadmap", "Changelog"],
  },
];

const socialChannels = ["X", "GitHub", "LinkedIn", "Discord"];

const getTimeLabel = () =>
  new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

const createLogEntry = (text, tag) => ({
  time: getTimeLabel(),
  text,
  tag,
});

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
  const [activityLog, setActivityLog] = useState([]);

  const canOpenWorkspace = Boolean(session.accountName && session.clientWorkspace);

  const appendActivity = (text, tag) => {
    setActivityLog((prev) => [createLogEntry(text, tag), ...prev].slice(0, MAX_LOG_ITEMS));
  };

  const handleAccessContinue = ({ accountName, clientWorkspace }) => {
    setSession({ accountName, clientWorkspace });
    setActivityLog([
      createLogEntry(`Workspace opened for ${accountName} in ${clientWorkspace}.`, "Session"),
      createLogEntry("Awaiting first document upload for local training updates.", "Data"),
      createLogEntry("Private model channel initialized for this workspace.", "Model"),
    ]);
    setStage("workspace");
  };

  const handleDocumentChange = ({ fileName, fileSize }) => {
    const sizeLabel = fileSize >= 1024 * 1024
      ? `${(fileSize / (1024 * 1024)).toFixed(1)} MB`
      : `${Math.max(1, Math.round(fileSize / 1024))} KB`;

    appendActivity(`Document staged: ${fileName} (${sizeLabel}).`, "Document");
    appendActivity("Local update extraction queued after validation checks.", "Pipeline");
  };

  const handlePromptSubmitted = (prompt) => {
    const trimmedPreview = prompt.length > 58 ? `${prompt.slice(0, 58)}...` : prompt;
    appendActivity(`Prompt submitted: "${trimmedPreview}"`, "Prompt");
    appendActivity("Learning signal generation triggered from latest interaction.", "Update");
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
            <UploadPanel onDocumentChange={handleDocumentChange} />
            <TrainingStatus />
            <UpdateLog updates={activityLog} />
          </div>

          <PrivacyBadge />
        </aside>

        <main className="workspace-main">
          <ChatPanel
            accountName={session.accountName}
            clientWorkspace={session.clientWorkspace}
            onPromptSubmitted={handlePromptSubmitted}
          />
        </main>
      </div>
    );
  };

  return (
    <div className="site-root">
      <header className="site-header">
        <div className="site-header-inner">
          <button
            className="brand-wordmark"
            type="button"
            onClick={() => setStage("landing")}
            aria-label="Go to landing page"
          >
            PrivaLoom
          </button>

          <nav className="site-nav" aria-label="Primary navigation">
            <button
              className={`site-nav-item ${stage === "landing" ? "is-active" : ""}`}
              type="button"
              onClick={() => setStage("landing")}
            >
              Research
            </button>
            <button className="site-nav-item" type="button" onClick={() => setStage("landing")}>
              Architecture
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

          <div className="site-header-actions">
            <span className="header-stage">{stageLabels[stage]}</span>
            {stage === "workspace" && canOpenWorkspace ? (
              <span className="header-account" title={`Active account: ${session.accountName}`}>
                {session.accountName}
              </span>
            ) : (
              <button className="header-login" type="button" onClick={() => setStage("access")}>
                Log in
              </button>
            )}
            <button
              className="header-cta"
              type="button"
              onClick={() => {
                if (canOpenWorkspace) {
                  setStage("workspace");
                  return;
                }

                setStage("access");
              }}
            >
              Try Workspace
            </button>
          </div>
        </div>
      </header>

      <main className="site-main">{renderStage()}</main>

      <footer className="site-footer">
        <div className="site-footer-inner">
          <div className="footer-grid">
            <section className="footer-column footer-brand-column">
              <p className="footer-brand">PrivaLoom</p>
              <p className="footer-description">
                A privacy-first distributed learning framework where local intelligence improves a
                shared model through compact update signals.
              </p>
            </section>

            {footerColumns.map((column) => (
              <section key={column.title} className="footer-column">
                <p className="footer-column-title">{column.title}</p>
                <ul className="footer-link-list">
                  {column.links.map((link) => (
                    <li key={link}>
                      <button className="footer-link-btn" type="button">
                        {link}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>

          <div className="footer-bottom">
            <div className="footer-socials" aria-label="Social channels">
              {socialChannels.map((channel) => (
                <button key={channel} className="footer-social-btn" type="button">
                  {channel}
                </button>
              ))}
            </div>
            <p className="footer-legal">PrivaLoom (c) 2026. Privacy-aware training by design.</p>
            <button className="footer-locale" type="button">
              English | Global
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}