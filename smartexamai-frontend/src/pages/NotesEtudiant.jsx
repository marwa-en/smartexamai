import { useEffect, useState } from 'react';
import api from '../api/client';
import * as endpoints from '../api/endpoints';
import { extractErrorMessage } from '../api/client';

export default function NotesEtudiant() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    endpoints
      .consulterNotes()
      .then((res) => setNotes(res.data))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleDownload() {
    setDownloading(true);
    try {
      const res = await api.get('/api/etudiant/releve', { responseType: 'blob' });
      const contentDisposition = res.headers['content-disposition'] || '';
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : 'releve_de_notes.pdf';
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(extractErrorMessage(err));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Mes notes</h1>
          <p className="text-muted">Retrouvez ici l'ensemble de vos résultats validés</p>
        </div>
        <button className="btn btn-primary" onClick={handleDownload} disabled={downloading}>
          <span className="material-icons">picture_as_pdf</span>
          {downloading ? 'Génération…' : 'Télécharger mon relevé'}
        </button>
      </div>

      {error && <div className="alert alert-warning">{error}</div>}

      <div className="card">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr><th>Examen</th><th>Matière</th><th>Date</th><th>Note</th><th>%</th><th>Statut</th><th>Commentaire</th></tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={7} className="text-muted">Chargement…</td></tr>}
              {!loading && notes.map((n, i) => (
                <tr key={i}>
                  <td>{n.examen}</td>
                  <td>{n.matiere}</td>
                  <td>{n.date_examen || '—'}</td>
                  <td>{n.note != null ? `${n.note}/${n.note_max}` : '—'}</td>
                  <td>{n.pourcentage != null ? `${n.pourcentage}%` : '—'}</td>
                  <td>
                    <span className={'badge ' + (n.valide_par_professeur ? 'badge-success' : 'badge-warning')}>
                      {n.valide_par_professeur ? 'Validée' : 'En attente'}
                    </span>
                  </td>
                  <td>{n.commentaire || '—'}</td>
                </tr>
              ))}
              {!loading && notes.length === 0 && (
                <tr><td colSpan={7} className="text-muted">Aucune note disponible pour le moment.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
