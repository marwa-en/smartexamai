import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';
import Modal from '../components/Modal';

export default function Classes() {
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ nom: '', niveau: '', annee_scolaire: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [etudiantsModal, setEtudiantsModal] = useState(null);
  const [etudiants, setEtudiants] = useState([]);

  function load() {
    setLoading(true);
    api.listClasses().then((res) => setClasses(res.data)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.createClasse(form);
      setModalOpen(false);
      setForm({ nom: '', niveau: '', annee_scolaire: '' });
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm('Supprimer cette classe ?')) return;
    try {
      await api.deleteClasse(id);
      load();
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  }

  async function showEtudiants(classe) {
    setEtudiantsModal(classe);
    const res = await api.listEtudiantsByClasse(classe.id);
    setEtudiants(res.data);
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Classes</h1>
          <p className="text-muted">Gérez les classes de l'établissement</p>
        </div>
        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          <span className="material-icons">add</span> Nouvelle classe
        </button>
      </div>

      <div className="card">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Niveau</th>
                <th>Année scolaire</th>
                <th>Étudiants</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={5} className="text-muted">Chargement…</td></tr>}
              {!loading && classes.map((c) => (
                <tr key={c.id}>
                  <td>{c.nom}</td>
                  <td>{c.niveau || '—'}</td>
                  <td>{c.annee_scolaire || '—'}</td>
                  <td>
                    <button className="btn btn-sm btn-outline" onClick={() => showEtudiants(c)}>
                      {c.nb_etudiants} étudiant(s)
                    </button>
                  </td>
                  <td className="table-actions">
                    <button className="btn-icon" onClick={() => handleDelete(c.id)}>
                      <span className="material-icons text-error">delete</span>
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && classes.length === 0 && (
                <tr><td colSpan={5} className="text-muted">Aucune classe.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modalOpen && (
        <Modal title="Nouvelle classe" onClose={() => setModalOpen(false)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-warning">{error}</div>}
            <div className="form-group">
              <label className="form-label">Nom</label>
              <input className="form-control" required value={form.nom}
                onChange={(e) => setForm({ ...form, nom: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Niveau</label>
              <input className="form-control" value={form.niveau}
                onChange={(e) => setForm({ ...form, niveau: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Année scolaire</label>
              <input className="form-control" placeholder="2025-2026" value={form.annee_scolaire}
                onChange={(e) => setForm({ ...form, annee_scolaire: e.target.value })} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={saving}>
              {saving ? 'Création…' : 'Créer la classe'}
            </button>
          </form>
        </Modal>
      )}

      {etudiantsModal && (
        <Modal title={`Étudiants — ${etudiantsModal.nom}`} onClose={() => setEtudiantsModal(null)}>
          <ul>
            {etudiants.map((e) => (
              <li key={e.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                {e.nom_complet} — <span className="text-muted">{e.cne || e.username}</span>
              </li>
            ))}
            {etudiants.length === 0 && <p className="text-muted">Aucun étudiant dans cette classe.</p>}
          </ul>
        </Modal>
      )}
    </>
  );
}
