import { useAuth } from '../context/AuthContext';

function initialsOf(user) {
  if (!user) return '';
  return `${(user.prenom || ' ')[0]}${(user.nom || ' ')[0]}`.toUpperCase();
}

const ROLE_LABELS = {
  admin: 'Administrateur',
  professeur: 'Professeur',
  etudiant: 'Étudiant',
};

export default function Navbar({ onToggleSidebar, title }) {
  const { user } = useAuth();

  return (
    <header className="navbar">
      <button className="btn-icon menu-toggle" onClick={onToggleSidebar}>
        <span className="material-icons">menu</span>
      </button>

      <div className="search-box">
        <span className="material-icons">search</span>
        <input type="text" placeholder={title || 'Rechercher…'} className="search-input" />
      </div>

      <div className="navbar-actions">
        <button className="btn-icon" title="Notifications">
          <span className="material-icons">notifications</span>
        </button>
        <div className="user-chip">
          <div className="avatar avatar-sm">{initialsOf(user)}</div>
          <div className="user-info">
            <div className="user-name">{user ? `${user.prenom} ${user.nom}` : ''}</div>
            <div className="user-role text-muted">{ROLE_LABELS[user?.role]}</div>
          </div>
          <span className="material-icons">expand_more</span>
        </div>
      </div>
    </header>
  );
}
