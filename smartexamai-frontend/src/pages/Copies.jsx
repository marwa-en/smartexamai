import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';

const STATUT_BADGE = {
  deposee: 'badge-neutral',
  en_correction: 'badge-warning',
  corrigee: 'badge-success',
  erreur: 'badge-error',
};

export default function Copies() {
  const [examens, setExamens] = useState([]);
  const [examenId, setExamenId] = useState('');
  const [allEtudiants, setAllEtudiants] = useState([]);
  const [etudiantId, setEtudiantId] = useState('');
  const [files, setFiles] = useState([]);
  const [copies, setCopies] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.listExamens().then((res) => setExamens(res.data));
    // Chargée une seule fois : la classe de chaque étudiant est déjà connue
    // depuis sa création (aucun appel supplémentaire par examen nécessaire).
    api.listUsers('etudiant').then((res) => setAllEtudiants(res.data));
  }, []);

  const examenCourant = examens.find((e) => e.id === Number(examenId));
  const etudiants = examenCourant
    ? allEtudiants.filter((et) => et.classe_id === examenCourant.classe_id)
    : [];

  useEffect(() => {
    if (!examenId) {
      setCopies([]);
      return;
    }
    api.listCopiesByExamen(examenId).then((res) => setCopies(res.data));
  }, [examenId]);

  async function handleUpload(e) {
    e.preventDefault();
    if (!examenId || !etudiantId || files.length === 0) return;
    setUploading(true);
    setError('');
    setMessage('');
    try {
      const formData = new FormData();
      formData.append('examen_id', examenId);
      formData.append('etudiant_id', etudiantId);
      Array.from(files).forEach((f) => formData.append('files', f));
      await api.deposerCopie(formData);
      setMessage('Copie déposée avec succès.');
      setFiles([]);
      const res = await api.listCopiesByExamen(examenId);
      setCopies(res.data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Copies scannées</h1>
          <p className="text-muted">Déposez les pages scannées d'une copie d'étudiant pour un examen</p>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Déposer une copie</span></div>
        {error && <div className="alert alert-warning">{error}</div>}
        {message && <div className="alert alert-success">{message}</div>}
        <form onSubmit={handleUpload}>
          <div className="form-group">
            <label className="form-label">Examen</label>
            <select className="select" style={{ width: '100%' }} required value={examenId}
              onChange={(e) => { setExamenId(e.target.value); setEtudiantId(''); }}>
              <option value="">— Choisir un examen —</option>
              {examens.map((ex) => (
                <option key={ex.id} value={ex.id}>{ex.titre} ({ex.classe_nom})</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">
              Étudiant (obligatoire — un même étudiant peut avoir plusieurs copies pour un examen)
            </label>
            <select className="select" style={{ width: '100%' }} required value={etudiantId}
              onChange={(e) => setEtudiantId(e.target.value)} disabled={!examenId}>
              <option value="">— Choisir l'étudiant —</option>
              {etudiants.map((et) => (
                <option key={et.id} value={et.id}>{et.nom_complet}</option>
              ))}
            </select>
            {examenId && etudiants.length === 0 && (
              <small className="text-muted">Aucun étudiant dans la classe de cet examen pour le moment.</small>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Pages scannées (images, une par page)</label>
            <div className="dropzone" onClick={() => document.getElementById('file-input').click()}>
              <span className="material-icons">document_scanner</span>
              <p>{files.length > 0 ? `${files.length} fichier(s) sélectionné(s)` : 'Cliquez pour choisir des images'}</p>
            </div>
            <input
              id="file-input"
              type="file"
              accept="image/*"
              multiple
              style={{ display: 'none' }}
              onChange={(e) => setFiles(e.target.files)}
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={uploading || !examenId || !etudiantId}>
            <span className="material-icons">upload</span>
            {uploading ? 'Envoi…' : 'Déposer la copie'}
          </button>
        </form>
      </div>

      {examenId && (
        <div className="card">
          <div className="card-header"><span className="card-title">Copies déposées pour cet examen</span></div>
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr><th>#</th><th>Étudiant</th><th>Statut</th><th>Déposée le</th></tr>
              </thead>
              <tbody>
                {copies.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>{c.etudiant_nom || <span className="text-muted">Non identifié</span>}</td>
                    <td><span className={'badge ' + (STATUT_BADGE[c.statut] || 'badge-neutral')}>{c.statut}</span></td>
                    <td>{new Date(c.created_at).toLocaleString('fr-FR')}</td>
                  </tr>
                ))}
                {copies.length === 0 && <tr><td colSpan={4} className="text-muted">Aucune copie déposée.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
