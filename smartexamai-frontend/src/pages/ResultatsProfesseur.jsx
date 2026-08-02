import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';
import Modal from '../components/Modal';

export default function ResultatsProfesseur() {
  const [examens, setExamens] = useState([]);
  const [examenId, setExamenId] = useState('');
  const [resultats, setResultats] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [ajustModal, setAjustModal] = useState(null);
  const [nouvelleNote, setNouvelleNote] = useState('');
  const [commentaire, setCommentaire] = useState('');
  const [detailModal, setDetailModal] = useState(null);

  useEffect(() => {
    api.mesExamens().then((res) => setExamens(res.data));
  }, []);

  function load(id) {
    if (!id) { setResultats([]); setStats(null); return; }
    setLoading(true);
    setError('');
    Promise.all([api.consulterResultats(id), api.statistiquesExamen(id)])
      .then(([r, s]) => { setResultats(r.data); setStats(s.data); })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => load(examenId), [examenId]);

  async function handleValider(resultatId) {
    try {
      await api.validerNote(resultatId, '');
      load(examenId);
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  }

  function openAjust(r) {
    setAjustModal(r);
    setNouvelleNote(r.note_finale ?? r.total_score ?? '');
    setCommentaire(r.commentaire_professeur || '');
  }

  async function handleAjuster(e) {
    e.preventDefault();
    try {
      await api.ajusterNote(ajustModal.id, Number(nouvelleNote), commentaire);
      setAjustModal(null);
      load(examenId);
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Résultats & notes</h1>
          <p className="text-muted">Consultez, validez et ajustez les notes générées par l'IA</p>
        </div>
      </div>

      <div className="card">
        <div className="form-group">
          <label className="form-label">Examen</label>
          <select className="select" style={{ width: '100%' }} value={examenId}
            onChange={(e) => setExamenId(e.target.value)}>
            <option value="">— Choisir un examen —</option>
            {examens.map((ex) => <option key={ex.id} value={ex.id}>{ex.titre} ({ex.classe_nom})</option>)}
          </select>
        </div>
      </div>

      {error && <div className="alert alert-warning">{error}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon primary"><span className="material-icons">fact_check</span></div>
            <div className="stat-info"><h4>Copies corrigées</h4><div className="stat-value">{stats.nombre_copies_corrigees}</div></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon success"><span className="material-icons">trending_up</span></div>
            <div className="stat-info"><h4>Moyenne</h4><div className="stat-value">{stats.moyenne ?? '—'}</div></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon info"><span className="material-icons">bar_chart</span></div>
            <div className="stat-info"><h4>Médiane</h4><div className="stat-value">{stats.mediane ?? '—'}</div></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon warning"><span className="material-icons">warning</span></div>
            <div className="stat-info"><h4>Échecs pipeline</h4><div className="stat-value">{stats.taux_echec_pipeline}%</div></div>
          </div>
        </div>
      )}

      {examenId && (
        <div className="card">
          <div className="card-header"><span className="card-title">Résultats des étudiants</span></div>
          {loading ? <p className="text-muted">Chargement…</p> : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr><th>Étudiant</th><th>Statut</th><th>Note</th><th>Validée</th><th></th></tr>
                </thead>
                <tbody>
                  {resultats.map((r) => (
                    <tr key={r.id}>
                      <td>{r.etudiant_nom || <span className="text-muted">Non identifié</span>}</td>
                      <td>
                        <span className={'badge ' + (r.statut === 'succes' ? 'badge-success' : 'badge-error')}>
                          {r.statut}
                        </span>
                      </td>
                      <td>{r.note_finale ?? r.total_score ?? '—'} / {r.max_score ?? '—'}</td>
                      <td>
                        <span className={'badge ' + (r.valide_par_professeur ? 'badge-success' : 'badge-warning')}>
                          {r.valide_par_professeur ? 'Oui' : 'Non'}
                        </span>
                      </td>
                      <td className="table-actions">
                        <button className="btn btn-sm btn-outline" onClick={() => setDetailModal(r)}>Détail</button>
                        <button className="btn btn-sm btn-outline" onClick={() => openAjust(r)}>Ajuster</button>
                        {!r.valide_par_professeur && (
                          <button className="btn btn-sm btn-primary" onClick={() => handleValider(r.id)}>Valider</button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {resultats.length === 0 && <tr><td colSpan={5} className="text-muted">Aucun résultat pour cet examen.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {ajustModal && (
        <Modal title={`Ajuster la note — ${ajustModal.etudiant_nom || 'étudiant'}`} onClose={() => setAjustModal(null)}>
          <form onSubmit={handleAjuster}>
            <div className="form-group">
              <label className="form-label">Nouvelle note</label>
              <input type="number" step="0.01" className="form-control" required
                value={nouvelleNote} onChange={(e) => setNouvelleNote(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Commentaire</label>
              <textarea className="form-control" rows={3} value={commentaire}
                onChange={(e) => setCommentaire(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Enregistrer</button>
          </form>
        </Modal>
      )}

      {detailModal && (
        <Modal title={`Détail — ${detailModal.etudiant_nom || 'étudiant'}`} onClose={() => setDetailModal(null)} width={640}>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, maxHeight: 400, overflowY: 'auto' }}>
            {JSON.stringify(detailModal, null, 2)}
          </pre>
        </Modal>
      )}
    </>
  );
}
