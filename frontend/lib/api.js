const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const CLIENT_ID_KEY = "privaloom_client_id";
const AUTH_TOKEN_KEY = "privaloom_auth_token";
const AUTH_USER_KEY = "privaloom_auth_user";

function normalizeError(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unknown request error";
}

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

function setAuthSession(payload) {
  if (!payload?.token || !payload?.user) {
    return;
  }

  localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(payload.user));
}

function clearAuthSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

function getAuthUser() {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function safeParseJson(text) {
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

async function request(path, options = {}) {
  const token = getAuthToken();

  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  const rawText = await response.text();
  const payload = safeParseJson(rawText);

  if (!response.ok) {
    if (response.status === 401) {
      clearAuthSession();
    }

    const detail =
      (payload && (payload.detail || payload.reason || payload.message)) || response.statusText;
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }

  return payload;
}

function createClientId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `client-${Date.now()}-${Math.floor(Math.random() * 1000000)}`;
}

export function getClientId() {
  const existing = localStorage.getItem(CLIENT_ID_KEY);
  if (existing) {
    return existing;
  }

  const nextId = createClientId();
  localStorage.setItem(CLIENT_ID_KEY, nextId);
  return nextId;
}

export async function getHealth() {
  return request("/");
}

export async function getFrontendOverview() {
  return request("/frontend/overview");
}

export async function sendChatPrompt(prompt) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function sendModelUpdate(weights) {
  return request("/send-update", {
    method: "POST",
    body: JSON.stringify({
      weights,
      client_id: getClientId(),
      timestamp: Math.floor(Date.now() / 1000),
    }),
  });
}

export async function register(username, password) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      username,
      password,
    }),
  });
}

export async function login(username, password) {
  const payload = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      username,
      password,
    }),
  });

  setAuthSession(payload);
  return payload;
}

export async function logout() {
  try {
    await request("/auth/logout", { method: "POST" });
  } finally {
    clearAuthSession();
  }
}

export async function getCurrentUser() {
  const payload = await request("/auth/me");
  if (payload?.user) {
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(payload.user));
  }
  return payload;
}

export async function listAuthUsers() {
  return request("/auth/users");
}

export async function createAuthUser(username, password = "", role = "user") {
  return request("/auth/users", {
    method: "POST",
    body: JSON.stringify({
      username,
      password: password || null,
      role,
    }),
  });
}

export async function deleteAuthUser(userId) {
  return request(`/auth/users/${encodeURIComponent(String(userId))}`, {
    method: "DELETE",
  });
}

export async function startUserSimulation(userId) {
  const payload = await request(`/auth/simulate/user/${encodeURIComponent(String(userId))}`, {
    method: "POST",
  });
  setAuthSession(payload);
  return payload;
}

export async function stopUserSimulation() {
  const payload = await request("/auth/simulate/stop", {
    method: "POST",
  });
  setAuthSession(payload);
  return payload;
}

export async function getSimulationMetrics() {
  return request("/simulation/metrics");
}

export async function getSimulationScenarios() {
  return request("/simulation/scenarios");
}

export function getApiBaseUrl() {
  return API_BASE;
}

export { clearAuthSession, getAuthToken, getAuthUser, normalizeError, setAuthSession };
