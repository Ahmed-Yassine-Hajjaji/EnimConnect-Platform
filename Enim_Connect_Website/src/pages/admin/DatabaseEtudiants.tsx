import React, { useEffect, useState } from "react";
import { api, type ImportEtudiantsResult } from "../../api/client";
import { NOMS_DEPARTEMENTS, DEPT_TO_FILIERES } from "../../constants/ensmr";

// ─── CSV helpers ──────────────────────────────────────────────────────────────
function csvEscape(value: string): string {
  const v = value ?? "";
  return /[",;\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

function downloadCsv(filename: string, rows: string[][]) {
  const content = rows.map((r) => r.map(csvEscape).join(",")).join("\r\n");
  // BOM pour qu'Excel ouvre l'UTF-8 correctement
  const blob = new Blob(["﻿" + content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const TEMPLATE_HEADER = ["nom", "prenom", "email", "filiere", "departement", "niveau"];
const TEMPLATE_EXEMPLE: string[][] = [
  ["Benali", "Yassine", "y.benali@enim.ac.ma", "Génie Informatique (GI)", "Département Informatique", "3A"],
  ["El Idrissi", "Salma", "s.elidrissi@enim.ac.ma", "Management Industriel (MGI)", "Département Génie Industriel", "2A"],
];

interface EtudiantAdmin {
  etudiant_id: string;
  nom: string;
  prenom: string;
  email: string;
  filiere?: string;
  departement?: string;
  niveau?: string;
  competences: string[];
  a_un_cv: boolean;
}

const COLORS = [
  "from-primary to-secondary",
  "from-secondary to-purple-500",
  "from-tertiary to-teal-500",
  "from-orange-500 to-amber-400",
  "from-green-500 to-emerald-400",
];

const DEPARTEMENTS_FILTER = ["Tous", ...NOMS_DEPARTEMENTS];
const NIVEAUX_FILTER = ["Tous", "1A", "2A", "3A"];
const NIVEAUX = ["1A", "2A", "3A"];

function initiales(nom: string, prenom: string) {
  return `${prenom?.[0] ?? ""}${nom?.[0] ?? ""}`.toUpperCase();
}

// ─── Reset Password Modal ─────────────────────────────────────────────────────
function ResetPasswordModal({ etudiant, onClose }: { etudiant: EtudiantAdmin; onClose: () => void }) {
  const [loading, setLoading] = useState(false);
  const [newPassword, setNewPassword] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleReset() {
    setLoading(true); setError(null);
    try {
      const res = await api.resetEtudiantPassword(etudiant.etudiant_id);
      setNewPassword(res.nouveau_mot_de_passe);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur lors de la réinitialisation");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-surface rounded-3xl border border-outline-variant shadow-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-headline font-bold text-on-surface text-lg">Réinitialiser le mot de passe</h2>
            <p className="text-sm text-on-surface-variant mt-0.5">{etudiant.prenom} {etudiant.nom} · {etudiant.email}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-surface-container transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        {!newPassword ? (
          <>
            <p className="text-sm text-on-surface-variant mb-5">
              Un nouveau mot de passe sécurisé sera généré. Le mot de passe actuel sera immédiatement invalidé.
            </p>
            {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">{error}</div>}
            <div className="flex gap-3">
              <button onClick={onClose} className="flex-1 btn-ghost">Annuler</button>
              <button onClick={handleReset} disabled={loading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-error text-white rounded-xl text-sm font-semibold hover:opacity-90 disabled:opacity-60">
                {loading && <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>}
                Réinitialiser
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="mb-5 p-4 bg-green-50 border border-green-200 rounded-xl">
              <p className="text-sm text-green-700 font-medium mb-2">Nouveau mot de passe :</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-sm font-mono bg-white border border-green-300 rounded-lg px-3 py-2 text-on-surface select-all">{newPassword}</code>
                <button onClick={() => navigator.clipboard.writeText(newPassword)} className="p-2 rounded-lg hover:bg-green-100" title="Copier">
                  <span className="material-symbols-outlined text-green-600 text-base">content_copy</span>
                </button>
              </div>
            </div>
            <p className="text-xs text-on-surface-variant mb-5">Transmettez ce mot de passe à l'étudiant. Il ne sera plus affiché après fermeture.</p>
            <button onClick={onClose} className="w-full btn-primary justify-center">Fermer</button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Delete Confirm Modal ─────────────────────────────────────────────────────
function DeleteEtudiantModal({ etudiant, onClose, onDeleted }: { etudiant: EtudiantAdmin; onClose: () => void; onDeleted: (id: string) => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setLoading(true); setError(null);
    try {
      await api.supprimerEtudiant(etudiant.etudiant_id);
      onDeleted(etudiant.etudiant_id);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur lors de la suppression");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-surface rounded-3xl border border-outline-variant shadow-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-error/10 flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-error text-xl">delete_forever</span>
            </div>
            <div>
              <h2 className="font-headline font-bold text-on-surface text-lg">Supprimer définitivement</h2>
              <p className="text-sm text-on-surface-variant mt-0.5">{etudiant.prenom} {etudiant.nom}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-surface-container transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>
        <div className="p-4 bg-error/5 border border-error/20 rounded-xl mb-5">
          <p className="text-sm text-on-surface">
            Cette action est <strong>irréversible</strong>. Le compte, le CV, les candidatures et toutes les données associées seront supprimés définitivement.
          </p>
        </div>
        {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">{error}</div>}
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 btn-ghost">Annuler</button>
          <button onClick={handleDelete} disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-error text-white rounded-xl text-sm font-semibold hover:opacity-90 disabled:opacity-60">
            {loading && <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>}
            Supprimer
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Create Student Modal ─────────────────────────────────────────────────────
function CreerEtudiantModal({ onClose, onCreated }: { onClose: () => void; onCreated: (e: EtudiantAdmin) => void }) {
  const [form, setForm] = useState({ email: "", password: "", nom: "", prenom: "", departement: "", filiere: "", niveau: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value, ...(field === "departement" ? { filiere: "" } : {}) }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.email || !form.password || !form.nom || !form.prenom) {
      setError("Email, mot de passe, nom et prénom sont obligatoires.");
      return;
    }
    setLoading(true); setError(null);
    try {
      await api.creerCompteEtudiant({
        email: form.email.trim(),
        password: form.password.trim(),
        nom: form.nom,
        prenom: form.prenom,
        filiere: form.filiere || undefined,
        departement: form.departement || undefined,
        niveau: form.niveau || undefined,
      });
      onCreated({
        etudiant_id: crypto.randomUUID(),
        nom: form.nom,
        prenom: form.prenom,
        email: form.email,
        filiere: form.filiere || undefined,
        departement: form.departement || undefined,
        niveau: form.niveau || undefined,
        competences: [],
        a_un_cv: false,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur lors de la création");
    } finally {
      setLoading(false);
    }
  }

  const filieres = DEPT_TO_FILIERES[form.departement] ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-surface rounded-3xl border border-outline-variant shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 pt-6 pb-4 border-b border-outline-variant flex items-center justify-between">
          <h2 className="font-headline font-bold text-on-surface text-lg">Créer un compte étudiant</h2>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-surface-container transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">{error}</div>}

          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-semibold text-on-surface mb-1.5">Prénom <span className="text-error">*</span></label>
              <input value={form.prenom} onChange={(e) => set("prenom", e.target.value)} required
                className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary" />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-semibold text-on-surface mb-1.5">Nom <span className="text-error">*</span></label>
              <input value={form.nom} onChange={(e) => set("nom", e.target.value)} required
                className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">Email <span className="text-error">*</span></label>
            <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} required
              placeholder="etudiant@enim.ac.ma"
              className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary" />
          </div>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">Mot de passe temporaire <span className="text-error">*</span></label>
            <input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} required
              placeholder="Min. 8 caractères"
              className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary" />
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-semibold text-on-surface mb-1.5">Département</label>
              <select value={form.departement} onChange={(e) => set("departement", e.target.value)}
                className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary">
                <option value="">— Choisir —</option>
                {NOMS_DEPARTEMENTS.map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-semibold text-on-surface mb-1.5">Niveau</label>
              <select value={form.niveau} onChange={(e) => set("niveau", e.target.value)}
                className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary">
                <option value="">— Choisir —</option>
                {NIVEAUX.map((n) => <option key={n}>{n}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">Filière</label>
            <select value={form.filiere} onChange={(e) => set("filiere", e.target.value)} disabled={!form.departement}
              className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary disabled:opacity-50">
              <option value="">— {form.departement ? "Choisir" : "Département d'abord"} —</option>
              {filieres.map((f) => <option key={f}>{f}</option>)}
            </select>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 btn-ghost">Annuler</button>
            <button type="submit" disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 btn-primary disabled:opacity-60">
              {loading && <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>}
              Créer le compte
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Import CSV Modal ─────────────────────────────────────────────────────────
function ImportEtudiantsModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportEtudiantsResult | null>(null);

  function telechargerModele() {
    downloadCsv("modele_import_etudiants.csv", [TEMPLATE_HEADER, ...TEMPLATE_EXEMPLE]);
  }

  function telechargerIdentifiants() {
    if (!result?.crees.length) return;
    downloadCsv("identifiants_etudiants.csv", [
      ["nom", "prenom", "email", "filiere", "departement", "niveau", "mot_de_passe"],
      ...result.crees.map((c) => [
        c.nom, c.prenom, c.email, c.filiere ?? "", c.departement ?? "", c.niveau ?? "", c.mot_de_passe,
      ]),
    ]);
  }

  async function handleSubmit() {
    if (!file) return;
    setLoading(true); setError(null);
    try {
      const res = await api.importEtudiants(file);
      setResult(res);
      if (res.crees.length > 0) onImported();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur lors de l'import");
    } finally {
      setLoading(false);
    }
  }

  const aReussi = result && result.crees.length > 0;
  const aEchoue = result && result.erreurs.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-surface rounded-3xl border border-outline-variant shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 pt-6 pb-4 border-b border-outline-variant flex items-center justify-between sticky top-0 bg-surface z-10">
          <div>
            <h2 className="font-headline font-bold text-on-surface text-lg">Importer des étudiants (CSV)</h2>
            <p className="text-sm text-on-surface-variant mt-0.5">Un compte est créé pour chaque ligne, avec mot de passe généré.</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-surface-container transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {!result && (
            <>
              {/* Exemple de format attendu */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-on-surface">Format attendu du fichier</h3>
                  <button onClick={telechargerModele} className="flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline">
                    <span className="material-symbols-outlined text-base">download</span>
                    Télécharger le modèle
                  </button>
                </div>
                <div className="rounded-xl border border-outline-variant overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-surface-container">
                        {TEMPLATE_HEADER.map((h) => (
                          <th key={h} className="text-left px-3 py-2 font-semibold text-on-surface-variant whitespace-nowrap">
                            {h}{["nom", "prenom", "email"].includes(h) && <span className="text-error"> *</span>}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant">
                      {TEMPLATE_EXEMPLE.map((row, i) => (
                        <tr key={i}>
                          {row.map((c, j) => (
                            <td key={j} className="px-3 py-2 text-on-surface-variant whitespace-nowrap">{c}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-on-surface-variant mt-2">
                  <span className="text-error">*</span> Colonnes obligatoires : <strong>nom, prenom, email</strong>.
                  Les colonnes <strong>filiere, departement, niveau</strong> (1A / 2A / 3A) sont optionnelles mais doivent correspondre aux valeurs officielles de l'ENSMR.
                  Séparateur virgule ou point-virgule, encodage UTF-8.
                </p>
              </div>

              {/* Upload */}
              <div>
                <label className="block text-sm font-semibold text-on-surface mb-1.5">Fichier CSV</label>
                <label className="flex items-center gap-3 border-2 border-dashed border-outline-variant rounded-xl px-4 py-4 cursor-pointer hover:border-primary transition-colors">
                  <span className="material-symbols-outlined text-on-surface-variant">upload_file</span>
                  <span className="text-sm text-on-surface-variant flex-1 truncate">{file ? file.name : "Choisir un fichier .csv…"}</span>
                  <input type="file" accept=".csv,text/csv" className="hidden"
                    onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError(null); }} />
                </label>
              </div>

              {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">{error}</div>}

              <div className="flex gap-3">
                <button onClick={onClose} className="flex-1 btn-ghost">Annuler</button>
                <button onClick={handleSubmit} disabled={!file || loading}
                  className="flex-1 flex items-center justify-center gap-2 btn-primary disabled:opacity-60">
                  {loading && <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>}
                  Importer
                </button>
              </div>
            </>
          )}

          {/* Résultat — échec (tout-ou-rien : rien n'a été créé) */}
          {aEchoue && (
            <div>
              <div className="p-4 bg-error/5 border border-error/20 rounded-xl mb-4">
                <p className="text-sm text-on-surface font-medium">
                  Aucun compte n'a été créé. {result!.erreurs.length} ligne(s) à corriger (import tout-ou-rien).
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant overflow-hidden max-h-72 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0">
                    <tr className="bg-surface-container">
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">Ligne</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">Email</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">Problème</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant">
                    {result!.erreurs.map((er, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 text-on-surface-variant">{er.ligne}</td>
                        <td className="px-3 py-2 text-on-surface-variant">{er.email || "—"}</td>
                        <td className="px-3 py-2 text-error">{er.raison}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-3 mt-5">
                <button onClick={() => { setResult(null); setFile(null); }} className="flex-1 btn-ghost">Réessayer</button>
                <button onClick={onClose} className="flex-1 btn-primary justify-center">Fermer</button>
              </div>
            </div>
          )}

          {/* Résultat — succès */}
          {aReussi && (
            <div>
              <div className="p-4 bg-green-50 border border-green-200 rounded-xl mb-4 flex items-center gap-3">
                <span className="material-symbols-outlined text-green-600">check_circle</span>
                <p className="text-sm text-green-700 font-medium">{result!.crees.length} compte(s) étudiant créé(s) avec succès.</p>
              </div>
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl mb-4">
                <p className="text-xs text-amber-800">
                  Téléchargez les identifiants <strong>maintenant</strong> : les mots de passe ne pourront plus être récupérés après fermeture.
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant overflow-hidden max-h-60 overflow-y-auto mb-4">
                <table className="w-full text-xs">
                  <thead className="sticky top-0">
                    <tr className="bg-surface-container">
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">Email</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">Mot de passe</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant">
                    {result!.crees.map((c, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 text-on-surface-variant">{c.email}</td>
                        <td className="px-3 py-2 font-mono text-on-surface select-all">{c.mot_de_passe}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-3">
                <button onClick={telechargerIdentifiants}
                  className="flex-1 flex items-center justify-center gap-2 btn-primary">
                  <span className="material-symbols-outlined text-base">download</span>
                  Télécharger les identifiants (CSV)
                </button>
                <button onClick={onClose} className="flex-1 btn-ghost">Fermer</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Bulk Delete Modal ────────────────────────────────────────────────────────
function BulkDeleteEtudiantsModal({ etudiants, onClose, onDeleted }: { etudiants: EtudiantAdmin[]; onClose: () => void; onDeleted: (ids: string[]) => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setLoading(true); setError(null);
    try {
      const ids = etudiants.map((e) => e.etudiant_id);
      await api.bulkDeleteEtudiants(ids);
      onDeleted(ids);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur lors de la suppression");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-surface rounded-3xl border border-outline-variant shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-error/10 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-error text-xl">delete_forever</span>
          </div>
          <div>
            <h2 className="font-headline font-bold text-on-surface text-lg">Supprimer {etudiants.length} étudiant{etudiants.length > 1 ? "s" : ""}</h2>
            <p className="text-sm text-on-surface-variant mt-0.5">Vérifiez la liste avant de confirmer.</p>
          </div>
        </div>

        <div className="p-3 bg-error/5 border border-error/20 rounded-xl mb-4">
          <p className="text-sm text-on-surface">
            Action <strong>irréversible</strong>. Les comptes, CV, candidatures et données associées seront supprimés définitivement.
          </p>
        </div>

        <div className="rounded-xl border border-outline-variant overflow-hidden max-h-60 overflow-y-auto mb-5">
          <table className="w-full text-xs">
            <tbody className="divide-y divide-outline-variant">
              {etudiants.map((e) => (
                <tr key={e.etudiant_id}>
                  <td className="px-3 py-2 font-medium text-on-surface">{e.prenom} {e.nom}</td>
                  <td className="px-3 py-2 text-on-surface-variant">{e.email}</td>
                  <td className="px-3 py-2 text-on-surface-variant">{e.niveau ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">{error}</div>}
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 btn-ghost">Annuler</button>
          <button onClick={handleDelete} disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-error text-white rounded-xl text-sm font-semibold hover:opacity-90 disabled:opacity-60">
            {loading && <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>}
            Confirmer la suppression
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function DatabaseEtudiants() {
  const [etudiants, setEtudiants] = useState<EtudiantAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [departement, setDepartement] = useState("Tous");
  const [niveau, setNiveau] = useState("Tous");
  const [cvFilter, setCvFilter] = useState<"tous" | "avec" | "sans">("tous");
  const [resetTarget, setResetTarget] = useState<EtudiantAdmin | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<EtudiantAdmin | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showBulkDelete, setShowBulkDelete] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  function chargerEtudiants() {
    setLoading(true);
    api.getEtudiants()
      .then((data) => setEtudiants(data as EtudiantAdmin[]))
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    chargerEtudiants();
  }, []);

  const filtered = etudiants.filter((e) => {
    const q = search.toLowerCase();
    const matchSearch = !q ||
      e.nom.toLowerCase().includes(q) ||
      e.prenom.toLowerCase().includes(q) ||
      e.email.toLowerCase().includes(q) ||
      (e.filiere ?? "").toLowerCase().includes(q) ||
      e.competences.some((c) => c.toLowerCase().includes(q));
    const matchDept = departement === "Tous" || e.departement === departement || e.filiere === departement;
    const matchNiveau = niveau === "Tous" || e.niveau === niveau;
    const matchCv = cvFilter === "tous" || (cvFilter === "avec" ? e.a_un_cv : !e.a_un_cv);
    return matchSearch && matchDept && matchNiveau && matchCv;
  });

  const stats = {
    total: etudiants.length,
    avec_cv: etudiants.filter((e) => e.a_un_cv).length,
  };

  const filteredIds = filtered.map((e) => e.etudiant_id);
  const tousSelectionnes = filteredIds.length > 0 && filteredIds.every((id) => selected.has(id));
  const selectionDansFiltre = filtered.filter((e) => selected.has(e.etudiant_id));

  function toggleSelection(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleToutSelectionner() {
    setSelected((prev) => {
      const next = new Set(prev);
      if (tousSelectionnes) {
        filteredIds.forEach((id) => next.delete(id));
      } else {
        filteredIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  function retirerDeSelection(ids: string[]) {
    setEtudiants((prev) => prev.filter((e) => !ids.includes(e.etudiant_id)));
    setSelected((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => next.delete(id));
      return next;
    });
  }

  return (
    <main className="min-h-screen flex flex-col">
      {resetTarget && <ResetPasswordModal etudiant={resetTarget} onClose={() => setResetTarget(null)} />}
      {deleteTarget && (
        <DeleteEtudiantModal
          etudiant={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onDeleted={(id) => setEtudiants((prev) => prev.filter((e) => e.etudiant_id !== id))}
        />
      )}
      {showCreate && (
        <CreerEtudiantModal
          onClose={() => setShowCreate(false)}
          onCreated={(e) => setEtudiants((prev) => [e, ...prev])}
        />
      )}
      {showImport && (
        <ImportEtudiantsModal
          onClose={() => setShowImport(false)}
          onImported={chargerEtudiants}
        />
      )}
      {showBulkDelete && (
        <BulkDeleteEtudiantsModal
          etudiants={selectionDansFiltre}
          onClose={() => setShowBulkDelete(false)}
          onDeleted={retirerDeSelection}
        />
      )}

      {/* Header */}
      <div className="sticky top-16 z-10 bg-surface/95 backdrop-blur-md border-b border-outline-variant px-4 sm:px-6 lg:px-10 py-4 lg:py-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h1 className="font-headline font-bold text-2xl text-on-surface">Base de données étudiants</h1>
            <p className="text-sm text-on-surface-variant mt-0.5">
              {loading ? "Chargement…" : `${filtered.length} étudiant${filtered.length !== 1 ? "s" : ""} · ${stats.avec_cv} avec CV`}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="text-center px-4 py-2 bg-surface-container-low rounded-xl border border-outline-variant">
              <div className="font-headline font-bold text-xl text-on-surface">{stats.total}</div>
              <div className="text-xs text-on-surface-variant">Total inscrits</div>
            </div>
            <div className="text-center px-4 py-2 bg-green-50 rounded-xl border border-green-200">
              <div className="font-headline font-bold text-xl text-green-600">{stats.avec_cv}</div>
              <div className="text-xs text-green-600">Avec CV</div>
            </div>
            <button onClick={() => setShowImport(true)} className="btn-ghost border border-outline-variant">
              <span className="material-symbols-outlined text-xl">upload_file</span>
              <span className="hidden sm:inline">Importer CSV</span>
              <span className="sm:hidden">Import</span>
            </button>
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              <span className="material-symbols-outlined text-xl">person_add</span>
              <span className="hidden sm:inline">Créer un étudiant</span>
              <span className="sm:hidden">Créer</span>
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 bg-surface-container border border-outline-variant rounded-xl px-3 py-2 flex-1 sm:flex-none sm:w-60">
            <span className="material-symbols-outlined text-on-surface-variant text-lg">search</span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Nom, email, compétence…"
              className="bg-transparent text-sm text-on-surface placeholder-on-surface-variant outline-none w-full"
            />
          </div>

          <select value={departement} onChange={(e) => setDepartement(e.target.value)}
            className="border border-outline-variant rounded-xl px-3 py-2 text-sm text-on-surface bg-surface outline-none focus:border-primary">
            {DEPARTEMENTS_FILTER.map((d) => <option key={d}>{d}</option>)}
          </select>

          <select value={niveau} onChange={(e) => setNiveau(e.target.value)}
            className="border border-outline-variant rounded-xl px-3 py-2 text-sm text-on-surface bg-surface outline-none focus:border-primary">
            {NIVEAUX_FILTER.map((n) => <option key={n}>{n}</option>)}
          </select>

          <div className="flex bg-surface-container rounded-xl p-1 gap-1">
            {(["tous", "avec", "sans"] as const).map((f) => (
              <button key={f} onClick={() => setCvFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  cvFilter === f ? "bg-white shadow-sm text-on-surface" : "text-on-surface-variant hover:text-on-surface"
                }`}>
                {f === "tous" ? "Tous" : f === "avec" ? "Avec CV" : "Sans CV"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Barre de sélection groupée */}
      {selectionDansFiltre.length > 0 && (
        <div className="sticky top-[8.5rem] z-[9] bg-primary/5 border-b border-primary/20 px-4 sm:px-6 lg:px-10 py-2.5 flex items-center justify-between gap-3">
          <span className="text-sm font-medium text-on-surface">
            {selectionDansFiltre.length} étudiant{selectionDansFiltre.length > 1 ? "s" : ""} sélectionné{selectionDansFiltre.length > 1 ? "s" : ""}
          </span>
          <div className="flex items-center gap-2">
            <button onClick={() => setSelected(new Set())} className="text-sm font-semibold text-on-surface-variant hover:text-on-surface px-3 py-1.5">
              Désélectionner
            </button>
            <button onClick={() => setShowBulkDelete(true)}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-error text-white text-sm font-semibold rounded-xl hover:opacity-90 transition-opacity">
              <span className="material-symbols-outlined text-base">delete</span>
              Supprimer la sélection
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="px-4 sm:px-6 lg:px-10 py-6 flex-1">
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <span className="material-symbols-outlined text-4xl animate-spin text-on-surface-variant">progress_activity</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <span className="material-symbols-outlined text-6xl text-on-surface-variant mb-4">people</span>
            <p className="font-semibold text-on-surface mb-2">Aucun étudiant trouvé</p>
            <p className="text-on-surface-variant text-sm">Modifiez vos critères de recherche.</p>
          </div>
        ) : (
          <div className="bg-surface-container-low rounded-2xl border border-outline-variant overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container">
                  <th className="px-5 py-3 w-10">
                    <input type="checkbox" checked={tousSelectionnes} onChange={toggleToutSelectionner}
                      className="w-4 h-4 rounded border-outline-variant accent-primary cursor-pointer" title="Tout sélectionner" />
                  </th>
                  {["Étudiant", "Email", "Filière / Département", "Niveau", "Compétences", "CV", "Actions"].map((h) => (
                    <th key={h} className="text-left px-5 py-3 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {filtered.map((e, i) => (
                  <tr key={e.etudiant_id} className={`hover:bg-surface-container/50 transition-colors ${selected.has(e.etudiant_id) ? "bg-primary/5" : ""}`}>
                    <td className="px-5 py-4">
                      <input type="checkbox" checked={selected.has(e.etudiant_id)} onChange={() => toggleSelection(e.etudiant_id)}
                        className="w-4 h-4 rounded border-outline-variant accent-primary cursor-pointer" />
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${COLORS[i % COLORS.length]} flex items-center justify-center text-white font-bold text-xs flex-shrink-0`}>
                          {initiales(e.nom, e.prenom)}
                        </div>
                        <div className="font-medium text-on-surface text-sm">{e.prenom} {e.nom}</div>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-sm text-on-surface-variant">{e.email}</td>
                    <td className="px-5 py-4 text-sm text-on-surface-variant">{e.filiere ?? e.departement ?? "—"}</td>
                    <td className="px-5 py-4">
                      {e.niveau ? (
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-primary/10 text-primary">{e.niveau}</span>
                      ) : <span className="text-sm text-on-surface-variant">—</span>}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-1">
                        {e.competences.slice(0, 3).map((c) => (
                          <span key={c} className="text-xs bg-surface-container text-on-surface-variant px-2 py-0.5 rounded-lg">{c}</span>
                        ))}
                        {e.competences.length > 3 && (
                          <span className="text-xs text-on-surface-variant">+{e.competences.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      {e.a_un_cv ? (
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-green-50 text-green-600 flex items-center gap-1 w-fit">
                          <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>description</span>
                          CV IA
                        </span>
                      ) : (
                        <span className="text-xs text-on-surface-variant">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setResetTarget(e)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-surface-container text-on-surface-variant text-xs font-semibold rounded-xl hover:bg-surface-container-high hover:text-on-surface transition-colors"
                          title="Réinitialiser le mot de passe"
                        >
                          <span className="material-symbols-outlined text-sm">lock_reset</span>
                          MDP
                        </button>
                        <button
                          onClick={() => setDeleteTarget(e)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-error/10 text-error text-xs font-semibold rounded-xl hover:bg-error/20 transition-colors"
                          title="Supprimer définitivement"
                        >
                          <span className="material-symbols-outlined text-sm">delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
