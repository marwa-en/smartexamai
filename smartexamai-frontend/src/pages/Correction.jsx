import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';

const STATUT_BADGE = {
  deposee: 'badge-neutral',
  en_correction: 'badge-warning',
  corrigee: 'badge-success',
  erreur: 'badge-error',
};

export default function Correction() {
  const [examens, setExamens] = useState([]);
  const [examenId, setExamenId] = useState('');
  const [copies, setCopies] = useState([]);
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.listExamens().then((res) => setExamens(res.data));
  }, []);

  function loadCopies(id) {
    if (!id) { setCopies([]); return; }
    api.listCopiesByExamen(id).then((res) => setCopies(res.data));
  }

  useEffect(() => loadCopies(examenId), [examenId]);

  function pushLog(text, type = 'info') {
    setLogs((prev) => [...prev, { text: `[${new Date().toLocaleTimeString('fr-FR')}] ${text}`, type }]);
  }

  async function corrigerUneCopie(copieId) {
    setBusyId(copieId);
    setError('');
    pushLog(`Lancement de la correction pour la copie #${copieId}…`);
    try {
      const res = await api.lancerCorrection(copieId);
      pushLog(`Copie #${copieId} — statut: ${res.data.statut}`, res.data.statut === 'erreur' ? 'err' : 'info');
      loadCopies(examenId);
    } catch (err) {
      const msg = extractErrorMessage(err);
      pushLog(`Erreur copie #${copieId}: ${msg}`, 'err');
      setError(msg);
    } finally {
      setBusyId(null);
    }
  }

  async function corrigerLot() {
    if (!examenId) return;
    setBusy(true);
    setError('');
    pushLog(`Lancement de la correction en lot pour l'examen #${examenId}…`);
    try {
      const res = await api.lancerCorrectionLot(examenId);
      pushLog(`Lot terminé : ${res.data.length} copie(s) traitée(s).`);
      loadCopies(examenId);
    } catch (err) {
      const msg = extractErrorMessage(err);
      pushLog(`Erreur lot: ${msg}`, 'err');
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Correction automatique (IA)</h1>
          <p className="text-muted">Déclenchez le pipeline de correction sur les copies déposées</p>
        </div>
      </div>

      {error && <div className="alert alert-warning">{error}</div>}

      <div className="card">
        <div className="card-header"><span className="card-title">Sélection de l'examen</span></div>
        <div className="form-group">
          <select className="select" style={{ width: '100%' }} value={examenId}
            onChange={(e) => setExamenId(e.target.value)}>
            <option value="">— Choisir un examen —</option>
            {examens.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.titre} ({ex.classe_nom}) — {ex.ressources?.is_complete ? 'ressources OK' : 'ressources incomplètes'}
              </option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" disabled={!examenId || busy} onClick={corrigerLot}>
          <span className="material-icons">smart_toy</span>
          {busy ? 'Correction en cours…' : 'Corriger toutes les copies de cet examen'}
        </button>
      </div>

      {examenId && (
        <div className="card">
          <div className="card-header"><span className="card-title">Copies de l'examen</span></div>
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr><th>#</th><th>Étudiant</th><th>Statut</th><th></th></tr>
              </thead>
              <tbody>
                {copies.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>{c.etudiant_nom || <span className="text-muted">Non identifié</span>}</td>
                    <td><span className={'badge ' + (STATUT_BADGE[c.statut] || 'badge-neutral')}>{c.statut}</span></td>
                    <td>
                      <button className="btn btn-sm btn-outline" disabled={busyId === c.id}
                        onClick={() => corrigerUneCopie(c.id)}>
                        {busyId === c.id ? 'En cours…' : 'Corriger'}
                      </button>
                    </td>
                  </tr>
                ))}
                {copies.length === 0 && <tr><td colSpan={4} className="text-muted">Aucune copie pour cet examen.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header"><span className="card-title">Journal du pipeline</span></div>
        <div className="log-console">
          {logs.map((l, i) => (
            <div key={i} className={`log-line ${l.type === 'err' ? 'log-err' : 'log-info'}`}>{l.text}</div>
          ))}
          {logs.length === 0 && <div className="log-line text-muted">Aucune action pour le moment.</div>}
        </div>
      </div>
    </>
  );
}
