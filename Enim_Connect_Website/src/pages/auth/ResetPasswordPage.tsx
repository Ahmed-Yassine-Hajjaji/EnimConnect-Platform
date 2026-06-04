import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../../api/client";
import usePageTitle from "../../hooks/usePageTitle";

export default function ResetPasswordPage() {
  usePageTitle("Réinitialisation du mot de passe");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (password !== confirm) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    setLoading(true);
    try {
      const res = await api.resetPassword(token, password);
      setSuccess(res.message);
      setPassword("");
      setConfirm("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-8 bg-surface">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8">
          <img
            src="/logo-enim-connect.svg"
            className="w-12 h-12 object-contain bg-white rounded-xl shadow-lg"
            alt="EnimConnect Logo"
          />
          <div>
            <div className="font-headline font-bold text-xl text-on-surface leading-tight">
              EnimConnect
            </div>
            <div className="text-xs text-on-surface-variant">Plateforme de stages</div>
          </div>
        </div>

        <div className="mb-6">
          <h2 className="font-headline font-bold text-xl text-on-surface mb-1">
            Nouveau mot de passe
          </h2>
          <p className="text-sm text-on-surface-variant">
            Choisissez un nouveau mot de passe pour votre compte.
          </p>
        </div>

        {!token && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">
            Lien invalide : aucun jeton de réinitialisation trouvé.
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">
            {error}
          </div>
        )}

        {success ? (
          <div className="space-y-5">
            <div className="p-3 bg-green-50 border border-green-200 text-green-700 text-sm rounded-xl">
              {success}
            </div>
            <button
              onClick={() => navigate("/")}
              className="w-full bg-gradient-to-r from-primary to-secondary text-white font-semibold py-3 rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-xl">login</span>
              Aller à la connexion
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-on-surface mb-2">
                Nouveau mot de passe
              </label>
              <div className="flex items-center gap-3 border border-outline-variant rounded-xl px-4 py-3 focus-within:border-primary transition-colors bg-surface-container-low">
                <span className="material-symbols-outlined text-on-surface-variant text-xl">lock</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Au moins 8 caractères"
                  required
                  className="flex-1 bg-transparent text-sm text-on-surface placeholder-on-surface-variant outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-on-surface mb-2">
                Confirmer le mot de passe
              </label>
              <div className="flex items-center gap-3 border border-outline-variant rounded-xl px-4 py-3 focus-within:border-primary transition-colors bg-surface-container-low">
                <span className="material-symbols-outlined text-on-surface-variant text-xl">lock</span>
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="flex-1 bg-transparent text-sm text-on-surface placeholder-on-surface-variant outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !token}
              className="w-full bg-gradient-to-r from-primary to-secondary text-white font-semibold py-3 rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {loading ? (
                <span className="material-symbols-outlined text-xl animate-spin">progress_activity</span>
              ) : (
                <span className="material-symbols-outlined text-xl">check</span>
              )}
              Réinitialiser le mot de passe
            </button>

            <button
              type="button"
              onClick={() => navigate("/")}
              className="w-full text-sm font-medium text-on-surface-variant hover:text-on-surface flex items-center justify-center gap-1"
            >
              <span className="material-symbols-outlined text-base">arrow_back</span>
              Retour à la connexion
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
