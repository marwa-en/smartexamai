import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';
import Modal from '../components/Modal';

const EMPTY_FORM = { titre: '', matiere_id: '', classe_id: '', professeur_id: '', date_examen: '' };

export default function Examens() {
  const [examens, setExamens] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [classes, setClasses] = useState([]);
  const [professeurs, setProfesseurs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  function load() {
    setLoading(true);
    Promise.all([api.listExamens(), api.listMatieres(), api.listClasses(), api.listUsers('professeur')])
      .then(([e, m, c, p]) => {
        setExamens(e.data);
        setMatieres(m.data);
        setClasses(c.data);
        setProfesseurs(p.data);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        titre: form.titre,
        matiere_id: Number(form.matiere_id),
        classe_id: Number(form.classe_id),
        professeur_id: form.professeur_id ? Number(form.professeur_id) : null,
        date_examen: form.date_examen || null,
      };
      await api.createExamen(payload);
      setModalOpen(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleAssign(examenId, professeurId) {
    await api.assignProfesseur(examenId, Number(professeurId));
    load();
  }

  async function handleDelete(id) {
    if (!confirm('Supprimer cet examen ?')) return;
    try {
      await api.deleteExamen(id);
      load();
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Examens</h1>
          <p className="text-muted">Créez les examens et assignez un professeur responsable</p>
        </div>
        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          <span className="material-icons">add</span> Nouvel examen
        </button>
      </div>

      <div className="card">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Titre</th>
                <th>Matière</th>
                <th>Classe</th>
                <th>Professeur</th>
                <th>Ressources</th>
                <th>Copies</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={7} className="text-muted">Chargement…</td></tr>}
              {!loading && examens.map((ex) => (
                <tr key={ex.id}>
                  <td>{ex.titre}</td>
                  <td>{ex.matiere_nom}</td>
                  <td>{ex.classe_nom}</td>
                  <td>
                    <select
                      className="select"
                      value={ex.professeur_id || ''}
                      onChange={(e) => handleAssign(ex.id, e.target.value)}
                    >
                      <option value="">— Non assigné —</option>
                      {professeurs.map((p) => (
                        <option key={p.id} value={p.id}>{p.nom_complet}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <span className={'badge ' + (ex.ressources?.is_complete ? 'badge-success' : 'badge-warning')}>
                      {ex.ressources?.is_complete ? 'Complètes' : 'Incomplètes'}
                    </span>
                  </td>
                  <td>{ex.nb_copies}</td>
                  <td className="table-actions">
                    <button className="btn-icon" onClick={() => handleDelete(ex.id)}>
                      <span className="material-icons text-error">delete</span>
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && examens.length === 0 && (
                <tr><td colSpan={7} className="text-muted">Aucun examen.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modalOpen && (
        <Modal title="Nouvel examen" onClose={() => setModalOpen(false)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-warning">{error}</div>}
            <div className="form-group">
              <label className="form-label">Titre</label>
              <input className="form-control" required value={form.titre}
                onChange={(e) => setForm({ ...form, titre: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Matière</label>
              <select className="select" style={{ width: '100%' }} required value={form.matiere_id}
                onChange={(e) => setForm({ ...form, matiere_id: e.target.value })}>
                <option value="">— Choisir —</option>
                {matieres.map((m) => <option key={m.id} value={m.id}>{m.nom}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Classe</label>
              <select className="select" style={{ width: '100%' }} required value={form.classe_id}
                onChange={(e) => setForm({ ...form, classe_id: e.target.value })}>
                <option value="">— Choisir —</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Professeur (optionnel)</label>
              <select className="select" style={{ width: '100%' }} value={form.professeur_id}
                onChange={(e) => setForm({ ...form, professeur_id: e.target.value })}>
                <option value="">— Non assigné —</option>
                {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Date de l'examen</label>
              <input type="date" className="form-control" value={form.date_examen}
                onChange={(e) => setForm({ ...form, date_examen: e.target.value })} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={saving}>
              {saving ? 'Création…' : 'Créer l’examen'}
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
