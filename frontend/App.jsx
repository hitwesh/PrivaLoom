import UploadPanel from "./components/UploadPanel";
import TrainingStatus from "./components/TrainingStatus";
import UpdateLog from "./components/UpdateLog";
import ChatPanel from "./components/ChatPanel";
import PrivacyBadge from "./components/PrivacyBadge";

export default function App() {
  return (
    <div className="app-shell">
      <aside className="workspace-sidebar">
        <section className="brand-block card-surface">
          <p className="eyebrow">PrivaLoom</p>
          <h1>Private AI Workspace</h1>
          <p className="brand-copy">
            A premium local console for secure dataset training, update monitoring,
            and model chat.
          </p>
        </section>

        <div className="sidebar-stack">
          <UploadPanel />
          <TrainingStatus />
          <UpdateLog />
        </div>

        <PrivacyBadge />
      </aside>

      <main className="workspace-main">
        <ChatPanel />
      </main>
    </div>
  );
}