import axios from 'axios';

// Si VITE_API_URL n'est pas défini, on utilise une URL relative : en dev,
// le proxy Vite (vite.config.js) redirige /api vers http://localhost:8000 ;
// en production, servez le frontend derrière le même domaine que l'API,
// ou définissez VITE_API_URL au moment du build.
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('smartexam_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('smartexam_token');
      localStorage.removeItem('smartexam_user');
      if (!window.location.pathname.startsWith('/login') && window.location.pathname !== '/') {
        window.location.href = '/';
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
