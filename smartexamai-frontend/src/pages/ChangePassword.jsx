import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { extractErrorMessage } from "../api/client";

export default function ChangePassword() {
  const [current, setCurrent] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");

    if (newPwd !== confirm) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/api/auth/change-password", {
        current_password: current,
        new_password: newPwd,
      });
      // Le backend révoque toutes les sessions → nettoyer et rediriger
      localStorage.removeItem('smartexam_token');
      localStorage.removeItem('smartexam_refresh');
      localStorage.removeItem('smartexam_user');
      alert("Mot de passe changé avec succès. Reconnectez-vous.");
      navigate("/login", { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 480, margin: "60px auto", padding: 20 }}>
      <h2>Changement de mot de passe obligatoire</h2>
      <p style={{ color: '#666', marginBottom: 20 }}>
        Vous utilisez un mot de passe initial. Définissez-en un nouveau
        (12 caractères min, majuscule, minuscule, chiffre).
      </p>

      {error && (
        <div className="alert alert-warning">
          <span className="material-icons" style={{ fontSize: 18, marginRight: 8 }}>error_outline</span>
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={submit}>
        <div className="form-group">
          <label className="form-label">Mot de passe actuel</label>
          <input
            type="password"
            className="form-control"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Nouveau mot de passe</label>
          <input
            type="password"
            className="form-control"
            value={newPwd}
            onChange={(e) => setNewPwd(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Confirmer le nouveau mot de passe</label>
          <input
            type="password"
            className="form-control"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-lg"
          style={{ width: '100%', marginTop: 20 }}
          disabled={loading}
        >
          {loading ? "Changement..." : "Changer le mot de passe"}
        </button>
      </form>
    </div>
  );
}