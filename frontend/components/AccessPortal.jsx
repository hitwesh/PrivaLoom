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

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!accountName.trim() || !password.trim()) {
      setError("Enter account name and password to continue.");
      return;
    }

    setError("");
    onContinue({
      accountName: accountName.trim(),
      clientWorkspace,
    });
  };

  return (
    <section className="access-shell">
      <form className="access-card card-surface" onSubmit={handleSubmit}>
        <p className="landing-eyebrow">Client Access</p>
        <h1>Choose account and workspace</h1>
        <p className="access-copy">
          Dummy sign-in page for multi-client simulation. This step is UI-only and does not use
          auth, RBAC, or database storage.
        </p>

        <label className="form-field">
          <span>Account name</span>
          <input
            className="field-input"
            type="text"
            placeholder="e.g. riya.training"
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
          <button className="btn-primary" type="submit">
            Open Workspace
          </button>
        </div>
      </form>
    </section>
  );
}
