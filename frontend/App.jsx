import { useEffect, useRef, useState } from "react";
import UploadPanel from "./components/UploadPanel";
import TrainingStatus from "./components/TrainingStatus";
import UpdateLog from "./components/UpdateLog";
import ChatPanel from "./components/ChatPanel";
import PrivacyBadge from "./components/PrivacyBadge";
import LandingPage from "./components/LandingPage";
import AccessPortal from "./components/AccessPortal";
import ArchitecturePage from "./components/ArchitecturePage";
import AdminPanel from "./components/AdminPanel";
import {
  createAuthUser,
  deleteAuthUser,
  getApiBaseUrl,
  getAuthUser,
  getClientId,
  getCurrentUser,
  getFrontendOverview,
  getHealth,
  login,
  logout,
  register,
  startUserSimulation,
  stopUserSimulation,
  listAuthUsers,
  normalizeError,
  sendChatPrompt,
  sendModelUpdate,
} from "./lib/api";
import { buildUpdateWeightsFromFiles } from "./lib/updatePayload";

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
    architecture: "Architecture",
    access: "Client Access",
    workspace: "Training Workspace",
  };

  const [stage, setStage] = useState("landing");
  const [session, setSession] = useState({
    accountName: "",
    clientWorkspace: "",
  });
  const [activityLog, setActivityLog] = useState([]);
  const [workspaceView, setWorkspaceView] = useState("chat");
  const [authUser, setAuthUser] = useState(getAuthUser());
  const [authUsers, setAuthUsers] = useState([]);
  const [backendOverview, setBackendOverview] = useState(null);
  const [backendError, setBackendError] = useState("");
  const [isBootstrappingWorkspace, setIsBootstrappingWorkspace] = useState(false);
  const [isRefreshingOverview, setIsRefreshingOverview] = useState(false);
  const [isManagingUsers, setIsManagingUsers] = useState(false);
  const [isLoadingAuthUsers, setIsLoadingAuthUsers] = useState(false);
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [lastTelemetrySyncAt, setLastTelemetrySyncAt] = useState(null);
  const previousOverviewRef = useRef(null);

  const hasAdminAccess = authUser?.role === "admin" && !authUser?.is_simulating;
  const canOpenWorkspace = Boolean(authUser && session.accountName && session.clientWorkspace);

  const appendActivity = (text, tag) => {
    setActivityLog((prev) => [createLogEntry(text, tag), ...prev].slice(0, MAX_LOG_ITEMS));
  };

  const formatAccessError = (error, authMode = "login") => {
    const message = normalizeError(error);

    if (message.includes("Failed to fetch") || message.includes("NetworkError")) {
      return `Cannot reach backend at ${getApiBaseUrl()}.`;
    }

    if (message.includes("HTTP 401")) {
      return "Invalid username or password.";
    }

    if (message.includes("username already exists")) {
      return authMode === "signup"
        ? "Account already exists. Switch to Log in."
        : "This account already exists. Please log in.";
    }

    if (message.includes("password must be at least 6 characters")) {
      return "Password must be at least 6 characters.";
    }

    return message;
  };

  const refreshAuthUsers = async () => {
    if (!hasAdminAccess) {
      setAuthUsers([]);
      return [];
    }

    setIsLoadingAuthUsers(true);
    try {
      const payload = await listAuthUsers();
      const users = Array.isArray(payload?.users) ? payload.users : [];
      setAuthUsers(users);
      return users;
    } finally {
      setIsLoadingAuthUsers(false);
    }
  };

  useEffect(() => {
    let isActive = true;

    const hydrate = async () => {
      if (!authUser) {
        setIsAuthReady(true);
        return;
      }

      try {
        const payload = await getCurrentUser();
        const nextUser = payload?.user || authUser;
        if (!isActive) {
          return;
        }

        setAuthUser(nextUser);
        setSession((prev) => ({
          accountName: nextUser?.username || prev.accountName,
          clientWorkspace: prev.clientWorkspace || "Aster Capital",
        }));
      } catch {
        if (isActive) {
          setAuthUser(null);
        }
      } finally {
        if (isActive) {
          setIsAuthReady(true);
        }
      }
    };

    hydrate();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (!hasAdminAccess) {
      setAuthUsers([]);
      return;
    }

    refreshAuthUsers().catch(() => {
      // Managed via panel feedback and auth errors.
    });
  }, [hasAdminAccess, authUser?.id]);

  useEffect(() => {
    if (workspaceView === "admin" && !hasAdminAccess) {
      setWorkspaceView("chat");
    }
  }, [workspaceView, hasAdminAccess]);

  const handleAccessContinue = async ({ authMode = "login", accountName, password, clientWorkspace }) => {
    setIsBootstrappingWorkspace(true);

    try {
      await getHealth();

      if (authMode === "signup") {
        await register(accountName, password);
        appendActivity(`New user account created for ${accountName}.`, "Auth");
      }

      const authPayload = await login(accountName, password);

      const nextAuthUser = authPayload?.user || null;
      setAuthUser(nextAuthUser);

      const overview = await getFrontendOverview();
      setBackendOverview(overview);
      previousOverviewRef.current = overview;
      setLastTelemetrySyncAt(Date.now());
      setBackendError("");

      const identityName = nextAuthUser?.username || accountName;
      setSession({ accountName: identityName, clientWorkspace });
      setWorkspaceView(nextAuthUser?.role === "admin" && !nextAuthUser?.is_simulating ? "admin" : "chat");
      setActivityLog([
        createLogEntry(`Workspace opened for ${identityName} in ${clientWorkspace}.`, "Session"),
        createLogEntry(
          `Connected to backend at ${getApiBaseUrl()} as ${identityName}.`,
          "Connectivity"
        ),
        createLogEntry(
          nextAuthUser?.role === "admin"
            ? "Admin role granted: governance controls enabled."
            : "User role granted: conversation and update controls enabled.",
          "Auth"
        ),
      ]);
      setStage("workspace");

      return { ok: true };
    } catch (error) {
      const message = formatAccessError(error, authMode);
      setBackendError(message);
      return { ok: false, error: message };
    } finally {
      setIsBootstrappingWorkspace(false);
    }
  };

  const handleDocumentChange = ({ fileName, fileSize }) => {
    const sizeLabel = fileSize >= 1024 * 1024
      ? `${(fileSize / (1024 * 1024)).toFixed(1)} MB`
      : `${Math.max(1, Math.round(fileSize / 1024))} KB`;

    appendActivity(`Document staged: ${fileName} (${sizeLabel}).`, "Document");
    appendActivity("Local update extraction queued after validation checks.", "Pipeline");
  };

  const handlePromptSubmitted = async (prompt) => {
    const trimmedPreview = prompt.length > 58 ? `${prompt.slice(0, 58)}...` : prompt;
    appendActivity(`Prompt submitted: "${trimmedPreview}"`, "Prompt");

    try {
      const result = await sendChatPrompt(prompt);
      appendActivity("Model response returned from /chat.", "Chat");
      return result.response || "No response received from model.";
    } catch (error) {
      const message = normalizeError(error);
      appendActivity(`Chat request failed: ${message}`, "Error");
      throw error;
    }
  };

  const handleSendDatasetUpdates = async ({ files }) => {
    if (!files?.length) {
      return { status: "skipped", reason: "no_files" };
    }

    const label = files.length === 1 ? files[0].fileName : `${files.length} files`;
    appendActivity(`Preparing update package from ${label}.`, "Dispatch");

    try {
      const weights = await buildUpdateWeightsFromFiles(files);
      const result = await sendModelUpdate(weights);

      if (result.status === "accepted") {
        appendActivity(
          `Update accepted. Buffer ${result.buffer_count}/${backendOverview?.status?.threshold ?? "?"}.`,
          "Update"
        );
      } else if (result.status === "rejected") {
        appendActivity(`Update rejected: ${result.reason}.`, "Validation");
      } else {
        appendActivity(`Update pipeline returned: ${result.status || "unknown"}.`, "Processing");
      }

      return result;
    } catch (error) {
      appendActivity(`Update dispatch failed: ${normalizeError(error)}`, "Error");
      throw error;
    }
  };

  const handleAdminActivity = (message, tag = "Admin") => {
    if (!message) {
      return;
    }

    appendActivity(message, tag);
  };

  const refreshOverview = async ({ silent = false } = {}) => {
    setIsRefreshingOverview(true);

    try {
      const overview = await getFrontendOverview();
      const previous = previousOverviewRef.current;

      setBackendOverview(overview);
      previousOverviewRef.current = overview;
      setLastTelemetrySyncAt(Date.now());
      setBackendError("");

      if (!silent) {
        appendActivity("Backend telemetry refreshed.", "Sync");
      }

      if (
        previous &&
        previous.status?.current_buffer_size > 0 &&
        overview.status?.current_buffer_size === 0 &&
        overview.status?.aggregation_stats?.total_rounds_completed >
          previous.status?.aggregation_stats?.total_rounds_completed
      ) {
        appendActivity(
          `Aggregation round ${overview.status?.aggregation_stats?.total_rounds_completed} completed.`,
          "Aggregation"
        );
      }

      return overview;
    } catch (error) {
      const message = normalizeError(error);
      setBackendError(message);

      if (!silent) {
        appendActivity(`Telemetry refresh failed: ${message}`, "Error");
      }

      throw error;
    } finally {
      setIsRefreshingOverview(false);
    }
  };

  const handleAdminAddUser = async (nextClientId) => {
    const normalized = String(nextClientId || "").trim();
    if (!normalized) {
      throw new Error("User ID cannot be empty.");
    }

    setIsManagingUsers(true);

    try {
      const result = await createAuthUser(normalized, "", "user");
      await refreshAuthUsers();
      await refreshOverview({ silent: true });
      appendActivity(`Admin registered user account ${normalized}.`, "Admin");
      return result;
    } catch (error) {
      appendActivity(`Admin add-user failed: ${normalizeError(error)}`, "Error");
      throw error;
    } finally {
      setIsManagingUsers(false);
    }
  };

  const handleAdminRemoveUser = async (targetUserId) => {
    const normalized = Number(targetUserId);
    if (!Number.isFinite(normalized) || normalized <= 0) {
      throw new Error("User ID is invalid.");
    }

    setIsManagingUsers(true);

    try {
      const result = await deleteAuthUser(normalized);
      await refreshAuthUsers();
      await refreshOverview({ silent: true });
      appendActivity(`Admin removed user account #${normalized}.`, "Admin");
      return result;
    } catch (error) {
      appendActivity(`Admin remove-user failed: ${normalizeError(error)}`, "Error");
      throw error;
    } finally {
      setIsManagingUsers(false);
    }
  };

  const handleAdminSimulateUser = async (targetUserId) => {
    const normalized = Number(targetUserId);
    if (!Number.isFinite(normalized) || normalized <= 0) {
      throw new Error("User ID is invalid.");
    }

    setIsManagingUsers(true);

    try {
      const payload = await startUserSimulation(normalized);
      const nextUser = payload?.user || null;
      setAuthUser(nextUser);
      if (nextUser?.username) {
        setSession((prev) => ({
          accountName: nextUser.username,
          clientWorkspace: prev.clientWorkspace || "Aster Capital",
        }));
      }
      setWorkspaceView("chat");
      await refreshOverview({ silent: true });
      appendActivity(`Admin simulation started for user #${normalized}.`, "Admin");
      return payload;
    } catch (error) {
      appendActivity(`Admin simulation failed: ${normalizeError(error)}`, "Error");
      throw error;
    } finally {
      setIsManagingUsers(false);
    }
  };

  const handleAdminStopSimulation = async () => {
    setIsManagingUsers(true);

    try {
      const payload = await stopUserSimulation();
      const nextUser = payload?.user || null;
      setAuthUser(nextUser);
      if (nextUser?.username) {
        setSession((prev) => ({
          accountName: nextUser.username,
          clientWorkspace: prev.clientWorkspace || "Aster Capital",
        }));
      }
      setWorkspaceView(nextUser?.role === "admin" ? "admin" : "chat");
      await refreshOverview({ silent: true });
      appendActivity("Admin simulation stopped.", "Admin");
      return payload;
    } catch (error) {
      appendActivity(`Failed to stop simulation: ${normalizeError(error)}`, "Error");
      throw error;
    } finally {
      setIsManagingUsers(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Session cleanup still proceeds locally.
    }

    setAuthUser(null);
    setAuthUsers([]);
    setBackendOverview(null);
    setBackendError("");
    setSession({
      accountName: "",
      clientWorkspace: "",
    });
    setWorkspaceView("chat");
    setStage("access");
  };

  useEffect(() => {
    if (stage !== "workspace") {
      return undefined;
    }

    let isActive = true;

    const pull = async (silent) => {
      if (!isActive) {
        return;
      }

      try {
        await refreshOverview({ silent });
      } catch {
        // Error is reflected in backendError state.
      }
    };

    pull(true);
    const interval = window.setInterval(() => {
      pull(true);
    }, 6000);

    return () => {
      isActive = false;
      window.clearInterval(interval);
    };
  }, [stage]);

  const renderStage = () => {
    if (stage === "landing") {
      return <LandingPage onStart={() => setStage("access")} />;
    }

    if (stage === "architecture") {
      return <ArchitecturePage onStart={() => setStage("access")} />;
    }

    if (stage === "access") {
      return (
        <AccessPortal
          onBack={() => setStage("landing")}
          onContinue={handleAccessContinue}
        />
      );
    }

    if (!isAuthReady) {
      return (
        <section className="access-shell">
          <div className="access-card card-surface">
            <p className="landing-eyebrow">Session</p>
            <h1>Restoring your authenticated workspace</h1>
            <p className="access-copy">Please wait while PrivaLoom validates your session.</p>
          </div>
        </section>
      );
    }

    if (!authUser) {
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
            <UploadPanel
              onDocumentChange={handleDocumentChange}
              onSendUpdates={handleSendDatasetUpdates}
            />
            <TrainingStatus
              overview={backendOverview}
              backendError={backendError}
              isRefreshing={isRefreshingOverview}
              clientId={getClientId()}
              lastTelemetrySyncAt={lastTelemetrySyncAt}
            />
            <UpdateLog updates={activityLog} />
          </div>

          <PrivacyBadge
            apiBaseUrl={getApiBaseUrl()}
            backendStatus={backendOverview?.status?.server_status}
          />
        </aside>

        <main className="workspace-main">
          <div className="workspace-main-shell">
            <section className="workspace-view-switcher card-surface" aria-label="Workspace view">
              <button
                className={`workspace-view-btn ${workspaceView === "chat" ? "is-active" : ""}`}
                type="button"
                onClick={() => setWorkspaceView("chat")}
              >
                Conversation
              </button>
              {hasAdminAccess ? (
                <button
                  className={`workspace-view-btn ${workspaceView === "admin" ? "is-active" : ""}`}
                  type="button"
                  onClick={() => setWorkspaceView("admin")}
                >
                  Admin Control
                </button>
              ) : null}
            </section>

            {workspaceView === "chat" ? (
              <ChatPanel
                accountName={session.accountName}
                clientWorkspace={session.clientWorkspace}
                onPromptSubmitted={handlePromptSubmitted}
                backendError={backendError}
                statusSummary={backendOverview?.status}
              />
            ) : (
              <AdminPanel
                accountName={session.accountName}
                clientWorkspace={session.clientWorkspace}
                clientId={getClientId()}
                updates={activityLog}
                overview={backendOverview}
                backendError={backendError}
                isRefreshing={isRefreshingOverview}
                isManagingUsers={isManagingUsers}
                isLoadingAuthUsers={isLoadingAuthUsers}
                lastTelemetrySyncAt={lastTelemetrySyncAt}
                authUser={authUser}
                authUsers={authUsers}
                onRefresh={() => refreshOverview({ silent: false })}
                onAddUser={handleAdminAddUser}
                onRemoveUser={handleAdminRemoveUser}
                onSimulateUser={handleAdminSimulateUser}
                onAdminActivity={handleAdminActivity}
              />
            )}
          </div>
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
            <button
              className={`site-nav-item ${stage === "architecture" ? "is-active" : ""}`}
              type="button"
              onClick={() => setStage("architecture")}
            >
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
            {authUser ? (
              <>
                <span
                  className="header-account"
                  title={`Active account: ${authUser.username} (${authUser.role})`}
                >
                  {authUser.username}
                  {authUser.is_simulating ? " (simulating)" : ""}
                </span>
                {authUser.is_simulating && authUser.actor_role === "admin" ? (
                  <button className="header-login" type="button" onClick={handleAdminStopSimulation}>
                    Stop Simulation
                  </button>
                ) : null}
                <button className="header-login" type="button" onClick={handleLogout}>
                  Log out
                </button>
              </>
            ) : (
              <div>
                <button className="header-login" type="button" onClick={() => setStage("access")}>
                  Log in
                </button>
                {isBootstrappingWorkspace ? (
                  <small className="header-syncing">Connecting...</small>
                ) : null}
              </div>
            )}
            <button
              className={`header-cta ${stage === "workspace" && canOpenWorkspace ? "is-workspace-active" : ""}`}
              type="button"
              disabled={stage === "workspace" && canOpenWorkspace}
              onClick={() => {
                if (canOpenWorkspace) {
                  setStage("workspace");
                  return;
                }

                setStage("access");
              }}
            >
              {stage === "workspace" && canOpenWorkspace ? "Workspace Active" : "Try Workspace"}
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