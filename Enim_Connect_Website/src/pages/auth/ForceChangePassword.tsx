import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../api/client";
import usePageTitle from "../../hooks/usePageTitle";

export default function ForceChangePassword() {
  usePageTitle("Changement de mot de passe obligatoire");
  const navigate = useNavigate();
  const { role, clearMustChangePassword } = useAuth();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    if (password !== confirm) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.forceChangePassword(password);
      // Update tokens
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      clearMustChangePassword();
      // Redirect to dashboard
      if (role === "etudiant") navigate("/etudiant/tableau-de-bord", { replace: true });
      else if (role === "entreprise") navigate("/entreprise/tableau-de-bord", { replace: true });
      else if (role === "club") navigate("/admin/interface", { replace: true });
      else navigate("/", { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur lors du changement de mot de passe");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <img
            src="/logo-enim-connect.svg"
            className="w-12 h-12 object-contain bg-white rounded-xl shadow-lg"
            alt="EnimConnect Logo"
          />
          <div>
            <div className="font-headline font-bold text-xl text-on-surface leading-tight">EnimConnect</div>
            <div className="text-xs text-on-surface-variant">Plateforme de stages</div>
          </div>
        </div>

        <div className="bg-surface-container-low border border-outline-variant rounded-2xl p-6 sm:p-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center">
              <span className="material-symbols-outlined text-orange-600 text-xl">lock_reset</span>
            </div>
            <div>
              <h1 className="font-headline font-bold text-lg text-on-surface">Changement obligatoire</h1>
              <p className="text-xs text-on-surface-variant">Première connexion</p>
            </div>
          </div>

          <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
            Pour des raisons de sécurité, vous devez choisir un nouveau mot de passe avant d'accéder à votre espace.
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-on-surface mb-2">
                Nouveau mot de passe
              </label>
              <div className="flex items-center gap-3 border border-outline-variant rounded-xl px-4 py-3 focus-within:border-primary transition-colors bg-surface">
                <span className="material-symbols-outlined text-on-surface-variant text-xl">lock</span>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 caractères"
                  required
                  className="flex-1 bg-transparent text-sm text-on-surface placeholder-on-surface-variant outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-on-surface-variant hover:text-on-surface transition-colors"
                >
                  <span className="material-symbols-outlined text-xl">
                    {showPassword ? "visibility_off" : "visibility"}
                  </span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-on-surface mb-2">
                Confirmer le mot de passe
              </label>
              <div className="flex items-center gap-3 border border-outline-variant rounded-xl px-4 py-3 focus-within:border-primary transition-colors bg-surface">
                <span className="material-symbols-outlined text-on-surface-variant text-xl">lock</span>
                <input
                  type={showPassword ? "text" : "password"}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Retapez le mot de passe"
                  required
                  className="flex-1 bg-transparent text-sm text-on-surface placeholder-on-surface-variant outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-primary to-secondary text-white font-semibold py-3 rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {loading ? (
                <span className="material-symbols-outlined text-xl animate-spin">progress_activity</span>
              ) : (
                <span className="material-symbols-outlined text-xl">check</span>
              )}
              Valider le nouveau mot de passe
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
