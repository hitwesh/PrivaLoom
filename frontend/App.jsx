import UploadPanel from "./components/UploadPanel";
import TrainingStatus from "./components/TrainingStatus";
import UpdateLog from "./components/UpdateLog";
import ChatPanel from "./components/ChatPanel";
import PrivacyBadge from "./components/PrivacyBadge";

export default function App() {
  return (
    <div className="container">
      <h1>Local AI Trainer Dashboard</h1>

      <div className="top-grid">
        <UploadPanel />
        <TrainingStatus />
        <UpdateLog />
      </div>

      <ChatPanel />
      <PrivacyBadge />
    </div>
  );
}