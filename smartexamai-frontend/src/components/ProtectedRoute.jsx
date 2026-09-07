import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <span className="material-icons" style={{ fontSize: 40, color: 'var(--primary, #3f51b5)' }}>
          hourglass_empty
        </span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  // ✅ FORCER le changement de mot de passe avant tout accès
  if (user.must_change_password) {
    return <Navigate to="/change-password" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to={`/${user.role}/dashboard`} replace />;
  }

  return children;
}