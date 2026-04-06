const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const CLIENT_ID_KEY = "privaloom_client_id";

function normalizeError(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unknown request error";
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
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const rawText = await response.text();
  const payload = safeParseJson(rawText);

  if (!response.ok) {
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

export async function getSimulationMetrics() {
  return request("/simulation/metrics");
}

export async function getSimulationScenarios() {
  return request("/simulation/scenarios");
}

export function getApiBaseUrl() {
  return API_BASE;
}

export { normalizeError };
