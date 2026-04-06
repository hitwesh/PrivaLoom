import { useState } from "react";

const workspaceOptions = [
  "Aster Capital",
  "Northline Health",
  "Helix Commerce",
  "Vertex Legal",
];

export default function AccessPortal({ onBack, onContinue }) {
  const [authMode, setAuthMode] = useState("login");
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

    if (authMode === "signup" && password.trim().length < 6) {
      setError("Password must be at least 6 characters to sign up.");
      return;
    }

    setError("");

    try {
      setIsSubmitting(true);
      const result = await onContinue({
        authMode,
        accountName: accountName.trim(),
        password,
        clientWorkspace,
      });

      if (result && result.ok === false) {
        setError(result.error || "Unable to open workspace.");
      }
    } catch {
      setError(`Unable to ${authMode === "signup" ? "sign up" : "log in"} right now. Please try again.`);
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

        <div className="access-mode-switch" role="tablist" aria-label="Authentication mode">
          <button
            type="button"
            role="tab"
            aria-selected={authMode === "login"}
            className={`access-mode-btn ${authMode === "login" ? "is-active" : ""}`}
            onClick={() => {
              setAuthMode("login");
              setError("");
            }}
          >
            Log in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={authMode === "signup"}
            className={`access-mode-btn ${authMode === "signup" ? "is-active" : ""}`}
            onClick={() => {
              setAuthMode("signup");
              setError("");
            }}
          >
            Sign up
          </button>
        </div>

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
            placeholder="Enter your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {authMode === "signup" ? (
          <p className="access-hint">Sign up passwords must be at least 6 characters.</p>
        ) : null}

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
            {isSubmitting
              ? authMode === "signup"
                ? "Creating account..."
                : "Signing in..."
              : authMode === "signup"
                ? "Create Account"
                : "Log in"}
          </button>
        </div>
      </form>
    </section>
  );
}
