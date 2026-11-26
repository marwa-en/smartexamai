import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
});

const TOKEN_KEY = 'smartexam_token';
const REFRESH_KEY = 'smartexam_refresh';
const USER_KEY = 'smartexam_user';

// ---------------------------------------------------------------------------
// Intercepteur requête : injecter le token
// ---------------------------------------------------------------------------
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// Refresh token : logique centralisée avec file d'attente
// ---------------------------------------------------------------------------
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
};

/**
 * Appelle /api/auth/refresh avec le refresh token stocké.
 * Utilise axios brut (pas `api`) pour éviter la boucle si /refresh retourne 401.
 * Retourne le NOUVEAU access token, ou null si échec.
 */
async function doRefresh() {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;

  try {
    const res = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
      refresh_token: refreshToken,
    });

    const data = res.data;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    if (data.refresh_token) {
      localStorage.setItem(REFRESH_KEY, data.refresh_token);
    }
    if (data.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    }
    return data.access_token;
  } catch {
    // Refresh échoué : session morte
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

/**
 * Si plusieurs requêtes échouent en 401 en même temps,
 * on ne fait qu'UN SEUL refresh, les autres attendent.
 */
function refreshAndWait() {
  if (!isRefreshing) {
    isRefreshing = true;
    return doRefresh().finally(() => {
      isRefreshing = false;
    });
  }
  // Une autre requête est déjà en train de refresh : on attend le résultat
  return new Promise((resolve, reject) => {
    failedQueue.push({ resolve, reject });
  });
}

// ---------------------------------------------------------------------------
// Intercepteur réponse : retry automatique après 401
// ---------------------------------------------------------------------------
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response &&
      error.response.status === 401 &&
      !originalRequest._retry &&
      localStorage.getItem(REFRESH_KEY)
    ) {
      originalRequest._retry = true;

      try {
        const newToken = await refreshAndWait();
        processQueue(null, newToken);

        if (!newToken) {
          // Refresh échoué : déconnexion
          if (!window.location.pathname.startsWith('/login') && window.location.pathname !== '/') {
            window.location.href = '/';
          }
          return Promise.reject(error);
        }

        // Rejouer la requête initiale avec le nouveau token
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        if (!window.location.pathname.startsWith('/login') && window.location.pathname !== '/') {
          window.location.href = '/';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export function extractErrorMessage(error) {
  if (error?.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
  }
  return error?.message || 'Une erreur est survenue.';
}

export default api;