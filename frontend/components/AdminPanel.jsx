import { useMemo, useState } from "react";

const seededUsers = [
  { name: "riya.training", updateCount: 31, lastSync: "4 min ago", status: "Healthy" },
  { name: "samik.ops", updateCount: 26, lastSync: "7 min ago", status: "Healthy" },
  { name: "hitesh.lead", updateCount: 19, lastSync: "10 min ago", status: "Review" },
  { name: "northline.audit", updateCount: 14, lastSync: "15 min ago", status: "Healthy" },
  { name: "vertex.legal", updateCount: 11, lastSync: "22 min ago", status: "Review" },
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

export default function AdminPanel({
  accountName,
  clientWorkspace,
  updates = [],
  onAdminActivity,
}) {
  const [integrityScore, setIntegrityScore] = useState(98.6);
  const [lastIntegrityRun, setLastIntegrityRun] = useState("Not yet run");
  const [lastRetrainRun, setLastRetrainRun] = useState("Not triggered");
  const [autoEnabled, setAutoEnabled] = useState(true);
  const [triggerMode, setTriggerMode] = useState("time");
  const [intervalHours, setIntervalHours] = useState(12);
  const [dataThresholdMb, setDataThresholdMb] = useState(512);
  const [modelQueueSize, setModelQueueSize] = useState(184);
  const [panelFeedback, setPanelFeedback] = useState("");

  const trackedTags = new Set(["Document", "Dispatch", "Processing", "Prompt", "Update"]);

  const currentUserCount = useMemo(
    () => updates.filter((entry) => trackedTags.has(entry.tag)).length,
    [updates]
  );

  const userRows = useMemo(() => {
    const currentUserName = accountName || "active.operator";
    const currentUserRow = {
      name: currentUserName,
      updateCount: Math.max(1, currentUserCount),
      lastSync: "just now",
      status: "Live",
    };

    const others = seededUsers.filter((entry) => entry.name !== currentUserName);
    return [currentUserRow, ...others];
  }, [accountName, currentUserCount]);

  const barData = useMemo(() => userRows.slice(0, 5), [userRows]);

  const maxBarValue = useMemo(
    () => Math.max(...barData.map((entry) => entry.updateCount), 1),
    [barData]
  );

  const integritySeries = useMemo(
    () => [97.7, 98.1, 98.0, 98.4, 98.2, 98.5, integrityScore],
    [integrityScore]
  );

  const chartPoints = useMemo(() => buildCoordinates(integritySeries, 520, 180, 14), [integritySeries]);

  const triggerActivity = (message, tag = "Admin") => {
    onAdminActivity?.(message, tag);
  };

  const handleIntegrityCheck = () => {
    const drift = Math.random() * 0.7 - 0.25;
    const nextScore = Number(Math.min(99.7, Math.max(96.8, integrityScore + drift)).toFixed(2));
    const stamp = formatNow();

    setIntegrityScore(nextScore);
    setLastIntegrityRun(stamp);
    setPanelFeedback(`Integrity check completed at ${stamp}. Current score: ${nextScore}%.`);
    triggerActivity(`Integrity check completed with score ${nextScore}%.`, "Integrity");
  };

  const handleManualRetrain = () => {
    const stamp = formatNow();
    const reducedQueue = Math.max(0, modelQueueSize - 42);

    setModelQueueSize(reducedQueue);
    setLastRetrainRun(stamp);
    setPanelFeedback(`Manual retraining queued at ${stamp}. Pending queue now ${reducedQueue} MB.`);
    triggerActivity("Manual retraining job queued by admin panel.", "Retrain");
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
      label: "Model checksum",
      status: integrityScore >= 98.0 ? "Healthy" : "Review",
    },
    {
      label: "Gradient drift monitor",
      status: integrityScore >= 97.5 ? "Healthy" : "Review",
    },
    {
      label: "Update anomaly scan",
      status: modelQueueSize < 600 ? "Healthy" : "Review",
    },
  ];

  return (
    <section className="admin-shell card-surface">
      <header className="admin-head">
        <div>
          <p className="admin-label">Admin Console</p>
          <h2>Model Governance and Retraining Control</h2>
          <p className="admin-copy">
            Monitor cross-user update activity, validate model integrity, and configure manual or
            automatic retraining policies for {clientWorkspace}.
          </p>
        </div>

        <article className="admin-integrity-pill">
          <span>Integrity score</span>
          <strong>{integrityScore}%</strong>
          <small>Last scan: {lastIntegrityRun}</small>
        </article>
      </header>

      <div className="admin-grid">
        <section className="admin-card">
          <div className="admin-card-head">
            <h3>Updates by user</h3>
            <span>Cross-workspace view</span>
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
            <span>Last 24h</span>
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
            <span>Recent checks</span>
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
            <span>Scheduler control</span>
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
            <button type="button" onClick={handleIntegrityCheck}>
              Check integrity
            </button>
            <button type="button" onClick={handleManualRetrain}>
              Manual retraining
            </button>
          </div>

          <div className="admin-meta-list">
            <p>
              <span>Active queue:</span>
              <strong>{modelQueueSize} MB</strong>
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
      </div>
    </section>
  );
}
