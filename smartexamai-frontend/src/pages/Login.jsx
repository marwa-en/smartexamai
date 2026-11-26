import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { extractErrorMessage } from '../api/client';

const ROLES = [
  { key: 'admin', icon: 'shield_person', title: 'Administrateur', desc: 'Gestion globale de la plateforme' },
  { key: 'professeur', icon: 'cast_for_education', title: 'Professeur', desc: 'Examens, correction & notes' },
  { key: 'etudiant', icon: 'school', title: 'Étudiant', desc: 'Consulter mes notes & relevés' },
];

export default function Login() {
  const [role, setRole] = useState('admin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

        async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await login(username, password);
      
      console.log('🔍 Result du login:', result);
      console.log('🔍 must_change_password:', result?.must_change_password);
      
      const u = result?.user || result;

      if (result?.must_change_password || u?.must_change_password) {
        console.log('🚀 Redirection forcée vers /change-password');
        // ✅ Utiliser window.location au lieu de navigate
        window.location.href = '/change-password';
        return;
      }

      navigate(`/${u.role}/dashboard`, { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div data-role={role}>
      <div className="login-wrapper">
        <div className="login-card" style={{ maxWidth: 480 }}>
          <div className="login-logo">
            <span className="material-icons">smart_toy</span>
            <h1>SmartExamAI</h1>
            <p className="text-muted">Plateforme intelligente de correction d'examens</p>
          </div>

          <div className="role-selector" style={{ margin: '24px 0' }}>
            {ROLES.map((r) => (
              <div
                key={r.key}
                className={'role-card' + (role === r.key ? ' selected' : '')}
                onClick={() => setRole(r.key)}
                style={{ padding: '18px 10px' }}
              >
                <span className="material-icons" style={{ fontSize: 32, marginBottom: 4 }}>{r.icon}</span>
                <h3 style={{ fontSize: 14 }}>{r.title}</h3>
                <p style={{ fontSize: 11 }}>{r.desc}</p>
              </div>
            ))}
          </div>

          {error && (
            <div className="alert alert-warning">
              <span className="material-icons" style={{ fontSize: 18 }}>error_outline</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Identifiant</label>
              <div className="input-icon">
                <span className="material-icons">person</span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="nom d'utilisateur"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Mot de passe</label>
              <div className="input-icon">
                <span className="material-icons">lock</span>
                <input
                  type="password"
                  className="form-control"
                  placeholder="••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%' }} disabled={loading}>
              <span className="material-icons">login</span>
              {loading ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>

          <div className="alert alert-info mt-24">
            <span className="material-icons" style={{ fontSize: 18 }}>info</span>
            <span>
              Le rôle sélectionné ne sert qu'au thème visuel : votre espace réel dépend de votre compte
              (créé par un administrateur).
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
