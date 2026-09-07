/**
 * SmartExamAI — Client API sécurisé.
 *
 * - Stocke access + refresh tokens
 * - Renouvelle automatiquement l'access token en cas de 401
 * - Évite les refresh simultanés (promesse partagée)
 * - Logout serveur-side
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const TOKEN_KEY = "smartexam_access_token";
const REFRESH_KEY = "smartexam_refresh_token";

// ---------------------------------------------------------------------------
// Stockage des tokens
// ---------------------------------------------------------------------------

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function saveTokens(data) {
  if (data.access_token) localStorage.setItem(TOKEN_KEY, data.access_token);
  if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// Refresh (avec promesse partagée anti-refresh-simultanés)
// ---------------------------------------------------------------------------

let refreshPromise = null;

async function doRefresh() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return null;

    const data = await res.json();
    saveTokens(data);
    return data.access_token;
  } catch {
    return null;
  }
}

function ensureRefresh() {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

// ---------------------------------------------------------------------------
// Requête générique avec retry automatique après refresh
// ---------------------------------------------------------------------------

export async function apiRequest(path, options = {}) {
  const buildHeaders = (token) => ({
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  });

  let res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: buildHeaders(getAccessToken()),
  });

  // 401 → tenter un refresh puis rejouer la requête UNE seule fois
  if (res.status === 401 && getRefreshToken()) {
    const newToken = await ensureRefresh();

    if (!newToken) {
      clearTokens();
      window.location.href = "/login";
      throw new Error("Session expirée. Veuillez vous reconnecter.");
    }

    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: buildHeaders(newToken),
    });
  }

  return res;
}

// ---------------------------------------------------------------------------
// Requête JSON (lève une erreur avec le detail FastAPI si échec)
// ---------------------------------------------------------------------------

export async function apiJson(path, options = {}) {
  const res = await apiRequest(path, options);

  if (!res.ok) {
    let detail = res.statusText || "Erreur serveur";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // réponse non-JSON
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Connexion échouée.");
  }

  const data = await res.json();
  saveTokens(data);
  return data;
}

export async function logout() {
  const refreshToken = getRefreshToken();

  try {
    if (refreshToken) {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    }
  } catch {
    // Même si le serveur est injoignable, on nettoie côté client
  } finally {
    clearTokens();
    window.location.href = "/login";
  }
}

export async function changePassword(current_password, new_password) {
  return apiJson("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password, new_password }),
  });
}