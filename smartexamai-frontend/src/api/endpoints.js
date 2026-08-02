import api from './client';

// --- Auth ---
export const login = (username, password) => api.post('/api/auth/login', { username, password });
export const me = () => api.get('/api/auth/me');

// --- Users (admin) ---
export const listUsers = (role) => api.get('/api/admin/users', { params: role ? { role } : {} });
export const createUser = (payload) => api.post('/api/admin/users', payload);
export const updateUser = (id, payload) => api.patch(`/api/admin/users/${id}`, payload);
export const deactivateUser = (id) => api.post(`/api/admin/users/${id}/deactivate`);
export const reactivateUser = (id) => api.post(`/api/admin/users/${id}/reactivate`);

// --- Classes (admin) ---
export const listClasses = () => api.get('/api/admin/classes');
export const createClasse = (payload) => api.post('/api/admin/classes', payload);
export const updateClasse = (id, payload) => api.patch(`/api/admin/classes/${id}`, payload);
export const deleteClasse = (id) => api.delete(`/api/admin/classes/${id}`);
export const listEtudiantsByClasse = (id) => api.get(`/api/admin/classes/${id}/etudiants`);

// --- Matières (admin) ---
export const listMatieres = () => api.get('/api/admin/matieres');
export const createMatiere = (payload) => api.post('/api/admin/matieres', payload);
export const updateMatiere = (id, payload) => api.patch(`/api/admin/matieres/${id}`, payload);
export const deleteMatiere = (id) => api.delete(`/api/admin/matieres/${id}`);

// --- Examens (admin + lecture prof) ---
export const listExamens = () => api.get('/api/admin/examens');
export const getExamen = (id) => api.get(`/api/admin/examens/${id}`);
export const createExamen = (payload) => api.post('/api/admin/examens', payload);
export const updateExamen = (id, payload) => api.patch(`/api/admin/examens/${id}`, payload);
export const deleteExamen = (id) => api.delete(`/api/admin/examens/${id}`);
export const assignProfesseur = (id, professeur_id) =>
  api.post(`/api/admin/examens/${id}/assign-professeur`, { professeur_id });

// --- Copies (admin) ---
export const listCopiesByExamen = (examenId) => api.get(`/api/admin/copies/by-examen/${examenId}`);
export const deposerCopie = (formData) =>
  api.post('/api/admin/copies', formData, { headers: { 'Content-Type': 'multipart/form-data' } });

// --- Correction (admin) ---
export const lancerCorrection = (copieId) => api.post(`/api/admin/correction/copies/${copieId}`);
export const lancerCorrectionLot = (examenId) => api.post(`/api/admin/correction/examens/${examenId}/lot`);

// --- Professeur ---
export const mesExamens = () => api.get('/api/professeur/examens');
export const definirRessources = (examenId, formData) =>
  api.post(`/api/professeur/examens/${examenId}/ressources`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const consulterResultats = (examenId) => api.get(`/api/professeur/examens/${examenId}/resultats`);
export const statistiquesExamen = (examenId) => api.get(`/api/professeur/examens/${examenId}/statistiques`);
export const validerNote = (resultatId, commentaire) =>
  api.post(`/api/professeur/resultats/${resultatId}/valider`, { commentaire });
export const ajusterNote = (resultatId, nouvelle_note, commentaire) =>
  api.post(`/api/professeur/resultats/${resultatId}/ajuster`, { nouvelle_note, commentaire });

// --- Étudiant ---
export const consulterNotes = () => api.get('/api/etudiant/notes');
export const releveUrl = () => `${api.defaults.baseURL}/api/etudiant/releve`;
