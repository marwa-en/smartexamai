import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as api from '../api/endpoints';

export default function DashboardEtudiant() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.consulterNotes().then((res) => setNotes(res.data)).finally(() => setLoading(false));
  }, []);

  const moyenne =
    notes.length > 0
      ? (notes.reduce((acc, n) => acc + (n.pourcentage || 0), 0) / notes.length).toFixed(1)
      : null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Bienvenue</h1>
          <p className="text-muted">Voici un aperçu de vos résultats</p>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon primary"><span className="material-icons">assignment_turned_in</span></div>
          <div className="stat-info">
            <h4>Examens corrigés</h4>
            <div className="stat-value">{notes.length}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon success"><span className="material-icons">grade</span></div>
          <div className="stat-info">
            <h4>Moyenne générale</h4>
            <div className="stat-value">{moyenne !== null ? `${moyenne}%` : '—'}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Notes récentes</span>
          <Link to="/etudiant/notes" className="btn btn-sm btn-outline">Voir toutes mes notes</Link>
        </div>
        {loading ? (
          <p className="text-muted">Chargement…</p>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Examen</th>
                  <th>Matière</th>
                  <th>Note</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {notes.slice(0, 5).map((n, i) => (
                  <tr key={i}>
                    <td>{n.examen}</td>
                    <td>{n.matiere}</td>
                    <td>{n.note != null ? `${n.note}/${n.note_max}` : '—'}</td>
                    <td>
                      <span className={'badge ' + (n.valide_par_professeur ? 'badge-success' : 'badge-warning')}>
                        {n.valide_par_professeur ? 'Validée' : 'En attente'}
                      </span>
                    </td>
                  </tr>
                ))}
                {notes.length === 0 && (
                  <tr><td colSpan={4} className="text-muted">Aucune note disponible pour le moment.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
