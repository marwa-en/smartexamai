import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';

import Login from './pages/Login';
import DashboardAdmin from './pages/DashboardAdmin';
import DashboardProfesseur from './pages/DashboardProfesseur';
import DashboardEtudiant from './pages/DashboardEtudiant';
import Utilisateurs from './pages/Utilisateurs';
import Classes from './pages/Classes';
import Matieres from './pages/Matieres';
import Examens from './pages/Examens';
import Copies from './pages/Copies';
import Correction from './pages/Correction';
import ExamensProfesseur from './pages/ExamensProfesseur';
import ResultatsProfesseur from './pages/ResultatsProfesseur';
import NotesEtudiant from './pages/NotesEtudiant';
import ChangePassword from './pages/ChangePassword';

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to={`/${user.role}/dashboard`} replace />;
  return <Login />;
}
function ChangePasswordGate() {
  const { user, loading } = useAuth();

  if (loading) return null;

  // Non connecté → retour accueil
  if (!user) return <Navigate to="/" replace />;

  // Mot de passe déjà changé → pas besoin d'y aller
  if (!user.must_change_password) {
    return <Navigate to={`/${user.role}/dashboard`} replace />;
  }

  return <ChangePassword />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          
          {/* ✅ Route publique pour changement de mot de passe */}
          {/* Nouveau ✅ */}
<Route path="/change-password" element={<ChangePasswordGate />} />

          {/* --- Admin --- */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={['admin']}>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="dashboard" element={<DashboardAdmin />} />
            <Route path="utilisateurs" element={<Utilisateurs />} />
            <Route path="classes" element={<Classes />} />
            <Route path="matieres" element={<Matieres />} />
            <Route path="examens" element={<Examens />} />
            <Route path="copies" element={<Copies />} />
            <Route path="correction" element={<Correction />} />
          </Route>

          {/* --- Professeur --- */}
          <Route
            path="/professeur"
            element={
              <ProtectedRoute roles={['professeur']}>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="dashboard" element={<DashboardProfesseur />} />
            <Route path="examens" element={<ExamensProfesseur />} />
            <Route path="resultats" element={<ResultatsProfesseur />} />
          </Route>

          {/* --- Étudiant --- */}
          <Route
            path="/etudiant"
            element={
              <ProtectedRoute roles={['etudiant']}>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="dashboard" element={<DashboardEtudiant />} />
            <Route path="notes" element={<NotesEtudiant />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}