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

export default function TrainingStatus({
  overview,
  backendError,
  isRefreshing,
  clientId,
  lastTelemetrySyncAt,
}) {
  const status = overview?.status;
  const serverOnline = Boolean(status?.server_status === "running" && !backendError);
  const currentBuffer = status?.current_buffer_size ?? 0;
  const threshold = status?.threshold ?? "-";
  const round = status?.aggregation_stats?.current_round ?? "-";
  const aggregationMethod = status?.security_config?.aggregation_method || "-";

  const statusItems = [
    {
      label: "Backend connectivity",
      state: serverOnline ? "done" : "waiting",
      stateLabel: serverOnline ? "Online" : "Offline",
    },
    {
      label: "Aggregation buffer",
      state: serverOnline && currentBuffer > 0 ? "done" : "waiting",
      stateLabel: `${currentBuffer}/${threshold}`,
    },
    {
      label: "Current round",
      state: serverOnline ? "done" : "waiting",
      stateLabel: String(round),
    },
    {
      label: "Aggregation method",
      state: serverOnline ? "done" : "waiting",
      stateLabel: String(aggregationMethod),
    },
  ];

  return (
    <section className="panel card-surface">
      <div className="panel-head">
        <h3>Training Status</h3>
        <span className="panel-kicker">Model</span>
      </div>

      <ul className="status-list">
        {statusItems.map((item) => (
          <li key={item.label} className="status-row">
            <span className="status-label">{item.label}</span>
            <span className={`status-pill ${item.state}`}>{item.stateLabel}</span>
          </li>
        ))}
      </ul>

      <p className="status-footnote">
        Client ID: {clientId?.slice(0, 8) || "-"}
        {` | Last backend sync: ${formatSyncAge(lastTelemetrySyncAt)}`}
        {isRefreshing ? " | Syncing telemetry..." : ""}
      </p>
      {backendError ? <p className="upload-feedback error">{backendError}</p> : null}
    </section>
  );
}
