import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';
import Modal from '../components/Modal';

export default function Matieres() {
  const [matieres, setMatieres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ nom: '', code: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  function load() {
    setLoading(true);
    api.listMatieres().then((res) => setMatieres(res.data)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.createMatiere(form);
      setModalOpen(false);
      setForm({ nom: '', code: '' });
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm('Supprimer cette matière ?')) return;
    try {
      await api.deleteMatiere(id);
      load();
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Matières</h1>
          <p className="text-muted">Gérez les matières enseignées</p>
        </div>
        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          <span className="material-icons">add</span> Nouvelle matière
        </button>
      </div>

      <div className="card">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Code</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={3} className="text-muted">Chargement…</td></tr>}
              {!loading && matieres.map((m) => (
                <tr key={m.id}>
                  <td>{m.nom}</td>
                  <td>{m.code || '—'}</td>
                  <td className="table-actions">
                    <button className="btn-icon" onClick={() => handleDelete(m.id)}>
                      <span className="material-icons text-error">delete</span>
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && matieres.length === 0 && (
                <tr><td colSpan={3} className="text-muted">Aucune matière.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modalOpen && (
        <Modal title="Nouvelle matière" onClose={() => setModalOpen(false)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-warning">{error}</div>}
            <div className="form-group">
              <label className="form-label">Nom</label>
              <input className="form-control" required value={form.nom}
                onChange={(e) => setForm({ ...form, nom: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Code</label>
              <input className="form-control" value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={saving}>
              {saving ? 'Création…' : 'Créer la matière'}
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
