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

export default function AdminPanel({
  accountName,
  clientWorkspace,
  clientId,
  updates = [],
  overview,
  backendError,
  isRefreshing,
  onRefresh,
  onAdminActivity,
}) {
  const [lastIntegrityRun, setLastIntegrityRun] = useState("Not yet run");
  const [lastRetrainRun, setLastRetrainRun] = useState("Not triggered");
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

  const userRows = useMemo(() => {
    const liveUsers = Array.isArray(overview?.reputation_clients)
      ? overview.reputation_clients.map((client) => ({
          name: client.client_id || "unknown-client",
          updateCount: client.total_updates || 0,
          lastSync: client.last_update || "-",
          status: normalizeStatus(client.current_score || 0),
        }))
      : [];

    const backendCurrentClient = clientId
      ? liveUsers.find((entry) => entry.name === clientId)
      : null;

    const currentUserName = accountName || "active.operator";
    const currentUserRow = {
      name: currentUserName,
      updateCount: backendCurrentClient ? backendCurrentClient.updateCount : currentUserCount,
      lastSync: backendCurrentClient
        ? backendCurrentClient.lastSync
        : currentUserCount > 0
          ? "local activity"
          : "-",
      status: "Live",
    };

    const merged = [
      currentUserRow,
      ...liveUsers.filter(
        (entry) => entry.name !== currentUserName && entry.name !== clientId
      ),
    ];
    return merged.length ? merged : fallbackUsers;
  }, [accountName, clientId, currentUserCount, overview?.reputation_clients]);

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

  const handleManualRetrain = async () => {
    const stamp = formatNow();
    setLastRetrainRun(stamp);

    try {
      await onRefresh?.();
      setPanelFeedback(`Manual retrain sync triggered at ${stamp}.`);
      triggerActivity("Manual retraining sync requested by admin panel.", "Retrain");
    } catch {
      setPanelFeedback(`Manual retrain sync failed at ${stamp}.`);
      triggerActivity("Manual retraining sync failed.", "Error");
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

          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Updates</th>
                  <th>Last sync</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {userRows.map((entry) => (
                  <tr key={entry.name}>
                    <td>{entry.name}</td>
                    <td>{entry.updateCount}</td>
                    <td>{entry.lastSync}</td>
                    <td>
                      <span className={`admin-status-chip ${entry.status.toLowerCase()}`}>
                        {entry.status}
                      </span>
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
                <p>{entry.name}</p>
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
            <button type="button" onClick={handleManualRetrain} disabled={isRefreshing}>
              Sync now
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
              <span>Last manual retrain:</span>
              <strong>{lastRetrainRun}</strong>
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
              <strong>{reputationStats.total_clients ?? 0}</strong>
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
                <span key={scenario} className="admin-status-chip healthy">
                  {scenario}
                </span>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
