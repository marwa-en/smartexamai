import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as api from '../api/endpoints';

export default function DashboardAdmin() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listUsers(), api.listClasses(), api.listMatieres(), api.listExamens()])
      .then(([users, classes, matieres, examens]) => {
        const u = users.data;
        setStats({
          admins: u.filter((x) => x.role === 'admin').length,
          professeurs: u.filter((x) => x.role === 'professeur').length,
          etudiants: u.filter((x) => x.role === 'etudiant').length,
          classes: classes.data.length,
          matieres: matieres.data.length,
          examens: examens.data.length,
          copies: examens.data.reduce((acc, e) => acc + (e.nb_copies || 0), 0),
        });
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Tableau de bord</h1>
          <p className="text-muted">Vue d'ensemble de la plateforme SmartExamAI</p>
        </div>
      </div>

      {loading ? (
        <p className="text-muted">Chargement…</p>
      ) : (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon primary"><span className="material-icons">group</span></div>
            <div className="stat-info">
              <h4>Professeurs</h4>
              <div className="stat-value">{stats.professeurs}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon success"><span className="material-icons">school</span></div>
            <div className="stat-info">
              <h4>Étudiants</h4>
              <div className="stat-value">{stats.etudiants}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon info"><span className="material-icons">menu_book</span></div>
            <div className="stat-info">
              <h4>Matières</h4>
              <div className="stat-value">{stats.matieres}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon warning"><span className="material-icons">assignment</span></div>
            <div className="stat-info">
              <h4>Examens</h4>
              <div className="stat-value">{stats.examens}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon accent"><span className="material-icons">document_scanner</span></div>
            <div className="stat-info">
              <h4>Copies déposées</h4>
              <div className="stat-value">{stats.copies}</div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header"><span className="card-title">Actions rapides</span></div>
        <div className="quick-actions">
          <Link to="/admin/utilisateurs" className="quick-action">
            <span className="material-icons">person_add</span>
            <span>Nouvel utilisateur</span>
          </Link>
          <Link to="/admin/classes" className="quick-action">
            <span className="material-icons">add_business</span>
            <span>Nouvelle classe</span>
          </Link>
          <Link to="/admin/examens" className="quick-action">
            <span className="material-icons">post_add</span>
            <span>Nouvel examen</span>
          </Link>
          <Link to="/admin/copies" className="quick-action">
            <span className="material-icons">upload_file</span>
            <span>Déposer des copies</span>
          </Link>
          <Link to="/admin/correction" className="quick-action">
            <span className="material-icons">smart_toy</span>
            <span>Lancer la correction</span>
          </Link>
        </div>
      </div>
    </>
  );
}
