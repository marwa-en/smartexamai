import { useEffect, useState } from 'react';
import * as api from '../api/endpoints';
import { extractErrorMessage } from '../api/client';

const ALL_SECTIONS = [
  { key: 'info', label: 'Identification étudiant' },
  { key: 'qcm', label: 'QCM' },
  { key: 'redaction', label: 'Rédaction' },
  { key: 'code', label: 'Exercice de code' },
];

const FILE_FIELDS = [
  { key: 'consignes', label: 'Consignes de l’examen (obligatoire)', required: true },
  { key: 'corrige', label: 'Corrigé type (obligatoire)', required: true },
  { key: 'unit_tests', label: 'Tests unitaires (obligatoire)', required: true },
  { key: 'code_consignes', label: 'Consignes exercice de code (si section code)', required: false },
  { key: 'cours', label: 'Support de cours (optionnel)', required: false },
  { key: 'bareme', label: 'Barème (optionnel)', required: false },
  { key: 'qcm_template', label: 'Modèle QCM (optionnel)', required: false },
  { key: 'qcm_answer_key', label: 'Corrigé QCM (optionnel)', required: false },
];

export default function ExamensProfesseur() {
  const [examens, setExamens] = useState([]);
  const [selected, setSelected] = useState(null);
  const [sections, setSections] = useState(['info', 'qcm', 'redaction', 'code']);
  const [scoringSystem, setScoringSystem] = useState('normal');
  const [codeLanguage, setCodeLanguage] = useState('python');
  const [files, setFiles] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  function load() {
    api.mesExamens().then((res) => setExamens(res.data));
  }

  useEffect(load, []);

  function select(examen) {
    setSelected(examen);
    setError('');
    setMessage('');
    const res = examen.ressources;
    setSections(res?.sections?.length ? res.sections : ['info', 'qcm', 'redaction', 'code']);
    setScoringSystem(res?.scoring_system || 'normal');
    setCodeLanguage(res?.code_language || 'python');
    setFiles({});
  }

  function toggleSection(key) {
    setSections((prev) => (prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selected) return;
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const formData = new FormData();
      const data = {
        sections,
        scoring_system: scoringSystem,
        code_language: codeLanguage,
      };
      formData.append('data', JSON.stringify(data));
      FILE_FIELDS.forEach(({ key }) => {
        if (files[key]) formData.append(key, files[key]);
      });
      await api.definirRessources(selected.id, formData);
      setMessage('Ressources enregistrées avec succès.');
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Mes examens</h1>
          <p className="text-muted">Déposez les ressources pédagogiques nécessaires à la correction automatique</p>
        </div>
      </div>

      <div className="card">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr><th>Titre</th><th>Matière</th><th>Classe</th><th>Ressources</th><th>Copies</th><th></th></tr>
            </thead>
            <tbody>
              {examens.map((ex) => (
                <tr key={ex.id}>
                  <td>{ex.titre}</td>
                  <td>{ex.matiere_nom}</td>
                  <td>{ex.classe_nom}</td>
                  <td>
                    <span className={'badge ' + (ex.ressources?.is_complete ? 'badge-success' : 'badge-warning')}>
                      {ex.ressources?.is_complete ? 'Complètes' : 'Incomplètes'}
                    </span>
                  </td>
                  <td>{ex.nb_copies}</td>
                  <td>
                    <button className="btn btn-sm btn-outline" onClick={() => select(ex)}>Gérer</button>
                  </td>
                </tr>
              ))}
              {examens.length === 0 && <tr><td colSpan={6} className="text-muted">Aucun examen assigné.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Ressources — {selected.titre}</span>
          </div>
          {error && <div className="alert alert-warning">{error}</div>}
          {message && <div className="alert alert-success">{message}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Sections à corriger</label>
              <div className="flex gap-16" style={{ flexWrap: 'wrap' }}>
                {ALL_SECTIONS.map((s) => (
                  <label key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <input type="checkbox" checked={sections.includes(s.key)} onChange={() => toggleSection(s.key)} />
                    {s.label}
                  </label>
                ))}
              </div>
            </div>

            <div className="flex gap-16">
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Système de notation QCM</label>
                <select className="select" style={{ width: '100%' }} value={scoringSystem}
                  onChange={(e) => setScoringSystem(e.target.value)}>
                  <option value="normal">Normal</option>
                  <option value="canadian">Canadien (points négatifs)</option>
                </select>
              </div>
              {sections.includes('code') && (
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Langage de l'exercice de code</label>
                  <select className="select" style={{ width: '100%' }} value={codeLanguage}
                    onChange={(e) => setCodeLanguage(e.target.value)}>
                    <option value="python">Python</option>
                    <option value="php">PHP</option>
                    <option value="java">Java</option>
                    <option value="c">C</option>
                  </select>
                </div>
              )}
            </div>

            {FILE_FIELDS.map(({ key, label }) => (
              <div className="form-group" key={key}>
                <label className="form-label">{label}</label>
                <input
                  type="file"
                  className="form-control"
                  onChange={(e) => setFiles((f) => ({ ...f, [key]: e.target.files[0] }))}
                />
                {selected.ressources?.[`${key}_path`] && !files[key] && (
                  <small className="text-muted">Déjà déposé — sélectionnez un fichier pour remplacer.</small>
                )}
              </div>
            ))}

            <button type="submit" className="btn btn-primary" disabled={saving}>
              <span className="material-icons">save</span>
              {saving ? 'Enregistrement…' : 'Enregistrer les ressources'}
            </button>
          </form>
        </div>
      )}
    </>
  );
}
