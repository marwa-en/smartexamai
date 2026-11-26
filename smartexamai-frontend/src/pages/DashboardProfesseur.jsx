import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as api from '../api/endpoints';

export default function DashboardProfesseur() {
  const [examens, setExamens] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.mesExamens().then((res) => setExamens(res.data)).finally(() => setLoading(false));
  }, []);

  const ressourcesCompletes = examens.filter((e) => e.ressources?.is_complete).length;
  const copiesTotal = examens.reduce((acc, e) => acc + (e.nb_copies || 0), 0);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Tableau de bord</h1>
          <p className="text-muted">Vos examens et vos copies à corriger</p>
        </div>
      </div>

      {loading ? (
        <p className="text-muted">Chargement…</p>
      ) : (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon primary"><span className="material-icons">assignment</span></div>
            <div className="stat-info">
              <h4>Examens assignés</h4>
              <div className="stat-value">{examens.length}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon success"><span className="material-icons">task_alt</span></div>
            <div className="stat-info">
              <h4>Ressources complètes</h4>
              <div className="stat-value">{ressourcesCompletes} / {examens.length}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon info"><span className="material-icons">document_scanner</span></div>
            <div className="stat-info">
              <h4>Copies déposées</h4>
              <div className="stat-value">{copiesTotal}</div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header"><span className="card-title">Mes examens récents</span></div>
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Titre</th>
                <th>Matière</th>
                <th>Classe</th>
                <th>Ressources</th>
                <th>Copies</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {examens.map((e) => (
                <tr key={e.id}>
                  <td>{e.titre}</td>
                  <td>{e.matiere_nom}</td>
                  <td>{e.classe_nom}</td>
                  <td>
                    <span className={'badge ' + (e.ressources?.is_complete ? 'badge-success' : 'badge-warning')}>
                      {e.ressources?.is_complete ? 'Complètes' : 'Incomplètes'}
                    </span>
                  </td>
                  <td>{e.nb_copies}</td>
                  <td>
                    <Link to="/professeur/examens" className="btn btn-sm btn-outline">Gérer</Link>
                  </td>
                </tr>
              ))}
              {examens.length === 0 && (
                <tr><td colSpan={6} className="text-muted">Aucun examen assigné pour le moment.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
