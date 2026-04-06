import { useMemo, useState } from "react";

const fallbackUsers = [
  { name: "no-clients-yet", updateCount: 0, lastSync: "-", status: "Review" },
];

const formatNow = () =>
  new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

const buildCoordinates = (values, width, height, padding) => {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const safeSteps = Math.max(values.length - 1, 1);

  return values.map((value, index) => {
    const x = padding + (index * (width - padding * 2)) / safeSteps;
    const y = height - padding - ((value - min) / range) * (height - padding * 2);

    return {
      x,
      y,
      value,
    };
  });
};

const toPercent = (value) => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }
  return Number((value * 100).toFixed(2));
};

const normalizeStatus = (score, threshold = 0.85) => (score >= threshold ? "Healthy" : "Review");

const formatSyncAge = (lastTelemetrySyncAt) => {
  if (!lastTelemetrySyncAt) {
    return "not synced yet";
  }

  const ageSeconds = Math.max(0, Math.floor((Date.now() - lastTelemetrySyncAt) / 1000));
  if (ageSeconds < 5) {
    return "just now";
  }
  if (ageSeconds < 60) {
    return `${ageSeconds}s ago`;
  }

  const ageMinutes = Math.floor(ageSeconds / 60);
  return `${ageMinutes}m ago`;
};

const shortenLabel = (value, maxLength = 22) => {
  const text = String(value || "-");
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1)}...`;
};

const formatScenarioLabel = (scenario) =>
  String(scenario || "")
    .toLowerCase()
    .replace(/[_-]+/g, " ");

const formatLastSync = (value) => {
  if (!value || value === "-") {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return shortenLabel(value, 18);
  }

  return parsed.toLocaleString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
};

const isSimulationUserId = (clientId) =>
  /^(honest_|gradient_scaling_|sign_flipping_|gradient_noise_|free_rider_|dropout_prone_|coordinated_malicious_)/.test(
    String(clientId || "")
  );

export default function AdminPanel({
  accountName,
  clientWorkspace,
  clientId,
  updates = [],
  overview,
  backendError,
  isRefreshing,
  isManagingUsers,
  lastTelemetrySyncAt,
  onRefresh,
  onAddUser,
  onRemoveUser,
  onAdminActivity,
}) {
  const [lastIntegrityRun, setLastIntegrityRun] = useState("Not yet run");
  const [lastRefreshRun, setLastRefreshRun] = useState("Not triggered");
  const [newUserId, setNewUserId] = useState("");
  const [autoEnabled, setAutoEnabled] = useState(true);
  const [triggerMode, setTriggerMode] = useState("time");
  const [intervalHours, setIntervalHours] = useState(12);
  const [dataThresholdMb, setDataThresholdMb] = useState(512);
  const [panelFeedback, setPanelFeedback] = useState("");

  const status = overview?.status || {};
  const securityStats = status.security_stats || {};
  const reputationStats = securityStats.reputation || {};
  const validationStats = securityStats.validation || {};
  const securityEventStats = securityStats.security_events || {};
  const simulation = overview?.simulation || {};

  const validationSuccessPercent = toPercent(validationStats.validation_success_rate);
  const rejectionRatePercent =
    typeof validationSuccessPercent === "number"
      ? Number((100 - validationSuccessPercent).toFixed(2))
      : null;

  const integrityScore = useMemo(() => {
    if (typeof validationSuccessPercent === "number") {
      return validationSuccessPercent;
    }

    const totalEvents = securityEventStats.total_events;
    if (typeof totalEvents === "number") {
      return Number(Math.max(70, 100 - totalEvents * 0.8).toFixed(2));
    }

    return 98.0;
  }, [securityEventStats.total_events, validationSuccessPercent]);

  const trackedTags = new Set(["Update"]);
  const currentUserCount = useMemo(
    () => updates.filter((entry) => trackedTags.has(entry.tag)).length,
    [updates]
  );

  const liveUsers = useMemo(
    () =>
      Array.isArray(overview?.reputation_clients)
        ? overview.reputation_clients.map((client) => ({
            name: client.client_id || "unknown-client",
            backendClientId: client.client_id || null,
            updateCount: client.total_updates || 0,
            lastSyncRaw: client.last_update || "-",
            lastSync: formatLastSync(client.last_update),
            status: normalizeStatus(client.current_score || 0),
            isSimulated: Boolean(client.is_simulated ?? isSimulationUserId(client.client_id)),
          }))
        : [],
    [overview?.reputation_clients]
  );

  const hiddenSimulationCount = useMemo(
    () => liveUsers.filter((entry) => entry.isSimulated).length,
    [liveUsers]
  );

  const visibleTrackedClientCount = useMemo(
    () => liveUsers.filter((entry) => !entry.isSimulated).length,
    [liveUsers]
  );

  const userRows = useMemo(() => {
    const visibleLiveUsers = liveUsers.filter((entry) => !entry.isSimulated);

    const backendCurrentClient = clientId
      ? liveUsers.find((entry) => entry.backendClientId === clientId)
      : null;

    const currentUserName = accountName || "active.operator";
    const currentUserRow = {
      name: currentUserName,
      backendClientId: backendCurrentClient?.backendClientId || null,
      updateCount: backendCurrentClient ? backendCurrentClient.updateCount : currentUserCount,
      lastSyncRaw: backendCurrentClient?.lastSyncRaw || "-",
      lastSync: backendCurrentClient
        ? backendCurrentClient.lastSync
        : currentUserCount > 0
          ? "local activity"
          : "-",
      status: "Live",
      isSimulated: false,
    };

    const merged = [
      currentUserRow,
      ...visibleLiveUsers.filter(
        (entry) => entry.name !== currentUserName && entry.backendClientId !== clientId
      ),
    ];
    return merged.length ? merged : fallbackUsers;
  }, [accountName, clientId, currentUserCount, liveUsers]);

  const barData = useMemo(() => userRows.slice(0, 5), [userRows]);
  const maxBarValue = useMemo(
    () => Math.max(...barData.map((entry) => entry.updateCount), 1),
    [barData]
  );

  const integritySeries = useMemo(() => {
    const base = [
      Math.max(0, integrityScore - 2.2),
      Math.max(0, integrityScore - 1.7),
      Math.max(0, integrityScore - 1.1),
      Math.max(0, integrityScore - 0.6),
      Math.max(0, integrityScore - 0.3),
      Math.max(0, integrityScore - 0.1),
      integrityScore,
    ];
    return base.map((value) => Number(value.toFixed(2)));
  }, [integrityScore]);

  const chartPoints = useMemo(
    () => buildCoordinates(integritySeries, 520, 180, 14),
    [integritySeries]
  );

  const triggerActivity = (message, tag = "Admin") => {
    onAdminActivity?.(message, tag);
  };

  const handleIntegrityCheck = async () => {
    const stamp = formatNow();
    setLastIntegrityRun(stamp);

    try {
      await onRefresh?.();
      setPanelFeedback(`Integrity check completed at ${stamp}. Current score: ${integrityScore}%.`);
      triggerActivity(`Integrity check completed with score ${integrityScore}%.`, "Integrity");
    } catch {
      setPanelFeedback(`Integrity check failed at ${stamp}.`);
      triggerActivity("Integrity check failed due to backend connectivity.", "Error");
    }
  };

  const handleTelemetryRefresh = async () => {
    const stamp = formatNow();
    setLastRefreshRun(stamp);

    try {
      await onRefresh?.();
      setPanelFeedback(`Telemetry refresh completed at ${stamp}.`);
      triggerActivity("Telemetry refresh requested by admin panel.", "Sync");
    } catch {
      setPanelFeedback(`Telemetry refresh failed at ${stamp}.`);
      triggerActivity("Telemetry refresh failed.", "Error");
    }
  };

  const handleAddUser = async () => {
    const normalized = newUserId.trim();
    if (!normalized) {
      setPanelFeedback("Enter a user ID before adding.");
      return;
    }

    try {
      const result = await onAddUser?.(normalized);
      const status = result?.status === "exists" ? "already exists" : "added";
      setPanelFeedback(`User ${normalized} ${status}.`);
      setNewUserId("");
      triggerActivity(`User ${normalized} ${status} from admin controls.`, "UserMgmt");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to add user.";
      setPanelFeedback(`Failed to add user: ${message}`);
      triggerActivity(`Failed to add user ${normalized}.`, "Error");
    }
  };

  const handleRemoveUser = async (entry) => {
    const targetId = entry?.backendClientId;
    if (!targetId) {
      return;
    }

    const confirmed = window.confirm(`Remove user ${targetId} from tracked clients?`);
    if (!confirmed) {
      return;
    }

    try {
      const result = await onRemoveUser?.(targetId);
      if (result?.status === "not_found") {
        setPanelFeedback(`User ${targetId} was already removed.`);
      } else {
        setPanelFeedback(`User ${targetId} removed.`);
      }
      triggerActivity(`User ${targetId} removed from admin controls.`, "UserMgmt");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to remove user.";
      setPanelFeedback(`Failed to remove user: ${message}`);
      triggerActivity(`Failed to remove user ${targetId}.`, "Error");
    }
  };

  const handlePolicySave = () => {
    const policyDescription =
      triggerMode === "time"
        ? `Auto retraining every ${intervalHours} hours`
        : `Auto retraining after ${dataThresholdMb} MB compiled data`;

    setPanelFeedback(`${policyDescription} policy saved.`);
    triggerActivity(`${policyDescription} policy updated.`, "Policy");
  };

  const integrityChecks = [
    {
      label: "Validation success rate",
      status: normalizeStatus((validationSuccessPercent || 0) / 100),
    },
    {
      label: "Outlier detection",
      status: status.security_config?.outlier_detection ? "Healthy" : "Review",
    },
    {
      label: "Reputation filtering",
      status: status.security_config?.reputation_enabled ? "Healthy" : "Review",
    },
  ];

  const scenarioNames = Array.isArray(simulation.scenarios) ? simulation.scenarios : [];

  return (
    <section className="admin-shell card-surface">
      <header className="admin-head">
        <div>
          <p className="admin-label">Admin Console</p>
          <h2>Model Governance and Retraining Control</h2>
          <p className="admin-copy">
            Live backend telemetry for {clientWorkspace}. Monitor security posture, update flow,
            and simulation readiness without leaving the workspace.
          </p>
        </div>

        <article className="admin-integrity-pill">
          <span>Integrity score</span>
          <strong>{integrityScore}%</strong>
          <small>Last scan: {lastIntegrityRun}</small>
        </article>
      </header>

      {backendError ? <p className="admin-feedback">Backend warning: {backendError}</p> : null}

      <div className="admin-grid">
        <section className="admin-card">
          <div className="admin-card-head">
            <h3>Updates by user</h3>
            <span>Reputation ledger</span>
          </div>

          <p className="admin-user-note">
            Simulation clients are hidden from this list.
            {hiddenSimulationCount > 0 ? ` Hidden now: ${hiddenSimulationCount}.` : ""}
          </p>

          <div className="admin-user-controls">
            <input
              className="admin-user-input"
              type="text"
              value={newUserId}
              onChange={(event) => setNewUserId(event.target.value)}
              placeholder="new user id"
              maxLength={128}
              disabled={isManagingUsers}
            />
            <button type="button" className="admin-user-add-btn" onClick={handleAddUser} disabled={isManagingUsers}>
              {isManagingUsers ? "Working..." : "Add user"}
            </button>
          </div>

          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Updates</th>
                  <th>Last sync</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {userRows.map((entry) => (
                  <tr key={entry.name}>
                    <td title={entry.name}>{shortenLabel(entry.name, 28)}</td>
                    <td>{entry.updateCount}</td>
                    <td title={entry.lastSyncRaw || entry.lastSync}>{entry.lastSync}</td>
                    <td>
                      <span className={`admin-status-chip ${entry.status.toLowerCase()}`}>
                        {entry.status}
                      </span>
                    </td>
                    <td>
                      {entry.backendClientId ? (
                        <button
                          type="button"
                          className="admin-user-remove-btn"
                          onClick={() => handleRemoveUser(entry)}
                          disabled={isManagingUsers}
                        >
                          Remove
                        </button>
                      ) : (
                        <span className="admin-user-action-muted">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="admin-card">
          <div className="admin-card-head">
            <h3>Update volume graph</h3>
            <span>Live workspace mix</span>
          </div>

          <div className="admin-bars">
            {barData.map((entry) => (
              <article key={entry.name} className="admin-bar-card">
                <div className="admin-bar-track">
                  <div
                    className="admin-bar-fill"
                    style={{ height: `${Math.round((entry.updateCount / maxBarValue) * 100)}%` }}
                  />
                </div>
                <p title={entry.name}>{shortenLabel(entry.name, 16)}</p>
                <span>{entry.updateCount} updates</span>
              </article>
            ))}
          </div>
        </section>

        <section className="admin-card">
          <div className="admin-card-head">
            <h3>Model integrity trend</h3>
            <span>Derived from validation</span>
          </div>

          <div className="admin-line-chart-wrap">
            <svg viewBox="0 0 520 180" role="img" aria-label="Model integrity trend chart">
              <polyline
                className="admin-line"
                points={chartPoints.map((point) => `${point.x},${point.y}`).join(" ")}
              />
              {chartPoints.map((point, index) => (
                <circle key={`point-${index}`} cx={point.x} cy={point.y} r="3.6" />
              ))}
            </svg>
          </div>

          <ul className="admin-check-list">
            {integrityChecks.map((check) => (
              <li key={check.label}>
                <span>{check.label}</span>
                <strong className={check.status.toLowerCase()}>{check.status}</strong>
              </li>
            ))}
          </ul>
        </section>

        <section className="admin-card">
          <div className="admin-card-head">
            <h3>Retraining policy</h3>
            <span>Operator controls</span>
          </div>

          <label className="admin-toggle">
            <input
              type="checkbox"
              checked={autoEnabled}
              onChange={(event) => setAutoEnabled(event.target.checked)}
            />
            <span>{autoEnabled ? "Auto retraining enabled" : "Auto retraining paused"}</span>
          </label>

          <div className="admin-mode-switch">
            <button
              className={triggerMode === "time" ? "is-active" : ""}
              type="button"
              onClick={() => setTriggerMode("time")}
            >
              Time based
            </button>
            <button
              className={triggerMode === "data" ? "is-active" : ""}
              type="button"
              onClick={() => setTriggerMode("data")}
            >
              Data threshold
            </button>
          </div>

          {triggerMode === "time" ? (
            <label className="admin-input-field">
              <span>Retrain interval (hours)</span>
              <input
                type="number"
                min="1"
                value={intervalHours}
                onChange={(event) => setIntervalHours(Number(event.target.value) || 1)}
              />
            </label>
          ) : (
            <label className="admin-input-field">
              <span>Compiled data trigger (MB)</span>
              <input
                type="number"
                min="50"
                value={dataThresholdMb}
                onChange={(event) => setDataThresholdMb(Number(event.target.value) || 50)}
              />
            </label>
          )}

          <div className="admin-action-row">
            <button type="button" onClick={handlePolicySave}>
              Save policy
            </button>
            <button type="button" onClick={handleIntegrityCheck} disabled={isRefreshing}>
              {isRefreshing ? "Refreshing..." : "Check integrity"}
            </button>
            <button type="button" onClick={handleTelemetryRefresh} disabled={isRefreshing}>
              Refresh telemetry
            </button>
          </div>

          <div className="admin-meta-list">
            <p>
              <span>Active buffer:</span>
              <strong>
                {status.current_buffer_size ?? 0}/{status.threshold ?? 0} updates
              </strong>
            </p>
            <p>
              <span>Last backend sync:</span>
              <strong>{formatSyncAge(lastTelemetrySyncAt)}</strong>
            </p>
            <p>
              <span>Last refresh request:</span>
              <strong>{lastRefreshRun}</strong>
            </p>
            <p>
              <span>Current operator:</span>
              <strong>{accountName || "unassigned"}</strong>
            </p>
          </div>

          {panelFeedback ? <p className="admin-feedback">{panelFeedback}</p> : null}
        </section>

        <section className="admin-card">
          <div className="admin-card-head">
            <h3>Security and Simulation</h3>
            <span>Backend feature map</span>
          </div>

          <div className="admin-meta-list">
            <p>
              <span>Aggregation method:</span>
              <strong>{status.security_config?.aggregation_method || "-"}</strong>
            </p>
            <p>
              <span>Byzantine tolerance:</span>
              <strong>{status.security_config?.byzantine_tolerance ?? "-"}</strong>
            </p>
            <p>
              <span>Total security events (24h):</span>
              <strong>{securityEventStats.total_events ?? 0}</strong>
            </p>
            <p>
              <span>Validation rejection rate:</span>
              <strong>
                {typeof rejectionRatePercent === "number" ? `${rejectionRatePercent}%` : "-"}
              </strong>
            </p>
            <p>
              <span>Tracked clients:</span>
              <strong>{visibleTrackedClientCount}</strong>
            </p>
            <p>
              <span>Simulation mode:</span>
              <strong>{simulation.enabled ? "Enabled" : "Disabled"}</strong>
            </p>
            <p>
              <span>Simulation scenarios:</span>
              <strong>{scenarioNames.length || 0}</strong>
            </p>
            <p>
              <span>Simulation current round:</span>
              <strong>{simulation.metrics?.current_round ?? "-"}</strong>
            </p>
          </div>

          {scenarioNames.length ? (
            <div className="admin-scenario-list">
              {scenarioNames.slice(0, 6).map((scenario) => (
                <span key={scenario} className="admin-status-chip healthy" title={scenario}>
                  {shortenLabel(formatScenarioLabel(scenario), 26)}
                </span>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
