import { useState } from "react";

const workspaceOptions = [
  "Aster Capital",
  "Northline Health",
  "Helix Commerce",
  "Vertex Legal",
];

export default function AccessPortal({ onBack, onContinue }) {
  const [accountName, setAccountName] = useState("");
  const [password, setPassword] = useState("");
  const [clientWorkspace, setClientWorkspace] = useState(workspaceOptions[0]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!accountName.trim() || !password.trim()) {
      setError("Enter account name and password to continue.");
      return;
    }

    setError("");

    try {
      setIsSubmitting(true);
      const result = await onContinue({
        accountName: accountName.trim(),
        clientWorkspace,
      });

      if (result && result.ok === false) {
        setError(result.error || "Unable to open workspace.");
      }
    } catch {
      setError("Unable to open workspace right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="access-shell">
      <form className="access-card card-surface" onSubmit={handleSubmit}>
        <p className="landing-eyebrow">Client Access</p>
        <h1>Choose account and workspace</h1>
        <p className="access-copy">
          Select your account identity and workspace context to continue into the private training
          console.
        </p>

        <label className="form-field">
          <span>Account name</span>
          <input
            className="field-input"
            type="text"
            placeholder="username"
            value={accountName}
            onChange={(event) => setAccountName(event.target.value)}
          />
        </label>

        <label className="form-field">
          <span>Password</span>
          <input
            className="field-input"
            type="password"
            placeholder="Enter any password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        <label className="form-field">
          <span>Client workspace</span>
          <select
            className="field-input"
            value={clientWorkspace}
            onChange={(event) => setClientWorkspace(event.target.value)}
          >
            {workspaceOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        {error ? <p className="access-error">{error}</p> : null}

        <div className="access-actions">
          <button className="btn-ghost" type="button" onClick={onBack}>
            Back
          </button>
          <button className="btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Connecting..." : "Open Workspace"}
          </button>
        </div>
      </form>
    </section>
  );
}
