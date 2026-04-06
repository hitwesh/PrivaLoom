export default function PrivacyBadge({ apiBaseUrl, backendStatus }) {
  return (
    <div className="privacy card-surface">
      <span className="privacy-dot" />
      Local deployment mode: prompts and updates are sent only to your configured backend ({apiBaseUrl}).
      {backendStatus === "running" ? " Server is reachable." : " Server is currently unreachable."}
    </div>
  );
}
