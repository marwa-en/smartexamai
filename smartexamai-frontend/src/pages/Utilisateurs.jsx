import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';
import Modal from '../components/Modal';

const EMPTY_FORM = {
  username: '',
  email: '',
  password: '',
  role: 'etudiant',
  nom: '',
  prenom: '',
  cne: '',
  classe_id: '',
};

const ROLE_LABELS = { admin: 'Administrateur', professeur: 'Professeur', etudiant: 'Étudiant' };

export default function Utilisateurs() {
  const [users, setUsers] = useState([]);
  const [classes, setClasses] = useState([]);
  const [roleFilter, setRoleFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  function load() {
    setLoading(true);
    Promise.all([api.listUsers(roleFilter || undefined), api.listClasses()])
      .then(([u, c]) => {
        setUsers(u.data);
        setClasses(c.data);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, [roleFilter]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setError('');
    setModalOpen(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = { ...form };
      if (payload.role !== 'etudiant') delete payload.classe_id;
      else payload.classe_id = payload.classe_id ? Number(payload.classe_id) : null;
      if (!payload.cne) delete payload.cne;
      await api.createUser(payload);
      setModalOpen(false);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(u) {
    if (u.is_active) await api.deactivateUser(u.id);
    else await api.reactivateUser(u.id);
    load();
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Utilisateurs</h1>
          <p className="text-muted">Gérez les comptes administrateurs, professeurs et étudiants</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          <span className="material-icons">person_add</span> Nouvel utilisateur
        </button>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Liste des utilisateurs</span>
          <select className="select" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
            <option value="">Tous les rôles</option>
            <option value="admin">Administrateurs</option>
            <option value="professeur">Professeurs</option>
            <option value="etudiant">Étudiants</option>
          </select>
        </div>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Identifiant</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Classe</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={7} className="text-muted">Chargement…</td></tr>
              )}
              {!loading && users.map((u) => (
                <tr key={u.id}>
                  <td>{u.nom_complet}</td>
                  <td>{u.username}</td>
                  <td>{u.email}</td>
                  <td><span className="badge badge-info">{ROLE_LABELS[u.role]}</span></td>
                  <td>{classes.find((c) => c.id === u.classe_id)?.nom || '—'}</td>
                  <td>
                    <span className={'badge ' + (u.is_active ? 'badge-success' : 'badge-error')}>
                      {u.is_active ? 'Actif' : 'Désactivé'}
                    </span>
                  </td>
                  <td className="table-actions">
                    <button className="btn btn-sm btn-outline" onClick={() => toggleActive(u)}>
                      {u.is_active ? 'Désactiver' : 'Réactiver'}
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && users.length === 0 && (
                <tr><td colSpan={7} className="text-muted">Aucun utilisateur.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modalOpen && (
        <Modal title="Nouvel utilisateur" onClose={() => setModalOpen(false)}>
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-warning">{error}</div>}

            <div className="form-group">
              <label className="form-label">Rôle</label>
              <select
                className="select"
                style={{ width: '100%' }}
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                <option value="etudiant">Étudiant</option>
                <option value="professeur">Professeur</option>
                <option value="admin">Administrateur</option>
              </select>
            </div>

            <div className="flex gap-16">
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Prénom</label>
                <input className="form-control" required value={form.prenom}
                  onChange={(e) => setForm({ ...form, prenom: e.target.value })} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Nom</label>
                <input className="form-control" required value={form.nom}
                  onChange={(e) => setForm({ ...form, nom: e.target.value })} />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Nom d'utilisateur</label>
              <input className="form-control" required value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </div>

            <div className="form-group">
              <label className="form-label">Email</label>
              <input type="email" className="form-control" required value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>

            <div className="form-group">
              <label className="form-label">Mot de passe</label>
              <input type="password" className="form-control" required value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>

            {form.role === 'etudiant' && (
              <>
                <div className="form-group">
                  <label className="form-label">CNE</label>
                  <input className="form-control" value={form.cne}
                    onChange={(e) => setForm({ ...form, cne: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Classe</label>
                  <select className="select" style={{ width: '100%' }} value={form.classe_id}
                    onChange={(e) => setForm({ ...form, classe_id: e.target.value })}>
                    <option value="">— Aucune —</option>
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>{c.nom}</option>
                    ))}
                  </select>
                </div>
              </>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={saving}>
              {saving ? 'Création…' : 'Créer l’utilisateur'}
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
