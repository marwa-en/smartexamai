import { createContext, useContext, useEffect, useState } from 'react';
import * as endpoints from '../api/endpoints';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('smartexam_user');
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('smartexam_token');
    if (!token) {
      setLoading(false);
      return;
    }
    endpoints
      .me()
      .then((res) => {
        setUser(res.data);
        localStorage.setItem('smartexam_user', JSON.stringify(res.data));
      })
      .catch(() => {
        localStorage.removeItem('smartexam_token');
        localStorage.removeItem('smartexam_user');
        setUser(null);
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function doLogin(username, password) {
    const res = await endpoints.login(username, password);
    localStorage.setItem('smartexam_token', res.data.access_token);
    localStorage.setItem('smartexam_user', JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  }

  function doLogout() {
    localStorage.removeItem('smartexam_token');
    localStorage.removeItem('smartexam_user');
    setUser(null);
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
