import { createContext, useContext, useEffect, useState } from 'react';
import * as endpoints from '../api/endpoints';

const AuthContext = createContext(null);

const TOKEN_KEY = 'smartexam_token';
const REFRESH_KEY = 'smartexam_refresh';
const USER_KEY = 'smartexam_user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    endpoints
      .me()
      .then((res) => {
        setUser(res.data);
        localStorage.setItem(USER_KEY, JSON.stringify(res.data));
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(USER_KEY);
        setUser(null);
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Login : stocke access + refresh tokens.
   * Retourne le PAYLOAD COMPLET (pas juste l'user) pour permettre
   * à Login.jsx de détecter must_change_password.
   */
   async function doLogin(username, password) {
    const res = await endpoints.login(username, password);
    const data = res.data;

    localStorage.setItem('smartexam_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('smartexam_refresh', data.refresh_token);
    }
    localStorage.setItem('smartexam_user', JSON.stringify(data.user));
    setUser(data.user);

    // ✅ CRUCIAL : retourner le PAYLOAD COMPLET, pas juste user
    return data;
  }

  /**
   * Logout serveur-side : révoque le refresh token.
   */
  async function doLogout() {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    try {
      if (refreshToken && endpoints.logoutApi) {
        await endpoints.logoutApi(refreshToken);
      }
    } catch {
      // Même si le serveur est injoignable, on nettoie côté client
    } finally {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      localStorage.removeItem(USER_KEY);
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login: doLogin, logout: doLogout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth doit être utilisé à l’intérieur de <AuthProvider>');
  return ctx;
}