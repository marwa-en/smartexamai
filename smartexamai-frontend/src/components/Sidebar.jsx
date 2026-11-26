import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const ROLE_LABELS = {
  admin: 'Espace Administrateur',
  professeur: 'Espace Professeur',
  etudiant: 'Espace Étudiant',
};

const ADMIN_LINKS = [
  { to: '/admin/dashboard', icon: 'dashboard', label: 'Tableau de bord' },
  { to: '/admin/utilisateurs', icon: 'group', label: 'Utilisateurs' },
  { to: '/admin/classes', icon: 'school', label: 'Classes' },
  { to: '/admin/matieres', icon: 'menu_book', label: 'Matières' },
  { to: '/admin/examens', icon: 'assignment', label: 'Examens' },
  { to: '/admin/copies', icon: 'document_scanner', label: 'Copies scannées' },
  { to: '/admin/correction', icon: 'smart_toy', label: 'Correction IA' },
];

const PROF_LINKS = [
  { to: '/professeur/dashboard', icon: 'dashboard', label: 'Tableau de bord' },
  { to: '/professeur/examens', icon: 'assignment', label: 'Mes examens' },
  { to: '/professeur/resultats', icon: 'fact_check', label: 'Résultats & notes' },
];

const ETUDIANT_LINKS = [
  { to: '/etudiant/dashboard', icon: 'dashboard', label: 'Tableau de bord' },
  { to: '/etudiant/notes', icon: 'grading', label: 'Mes notes' },
];

function linksForRole(role) {
  if (role === 'admin') return ADMIN_LINKS;
  if (role === 'professeur') return PROF_LINKS;
  if (role === 'etudiant') return ETUDIANT_LINKS;
  return [];
}

export default function Sidebar({ open }) {
  const { user, logout } = useAuth();
  const links = linksForRole(user?.role);

  return (
    <aside className={`sidebar${open ? ' open' : ''}`}>
      <div className="sidebar-header">
        <span className="material-icons" style={{ color: 'var(--primary)', fontSize: 32 }}>
          smart_toy
        </span>
        <div>
          <h3 style={{ fontSize: 16, margin: 0 }}>SmartExamAI</h3>
          <small className="text-muted">{ROLE_LABELS[user?.role] || 'Espace'}</small>
        </div>
      </div>

      <nav className="sidebar-nav">
        <ul className="nav-list">
          {links.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
              >
                <span className="material-icons">{link.icon}</span>
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="nav-divider"></div>
        <ul className="nav-list">
          <li>
            <a href="#" className="nav-link logout-link" onClick={(e) => { e.preventDefault(); logout(); }}>
              <span className="material-icons">logout</span>
              Déconnexion
            </a>
          </li>
        </ul>
      </nav>
    </aside>
  );
}
