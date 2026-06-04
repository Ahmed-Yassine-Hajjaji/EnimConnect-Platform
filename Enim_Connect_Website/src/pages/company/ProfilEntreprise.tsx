import { useEffect, useRef, useState } from 'react';
import { api, type EntrepriseProfile } from '../../api/client';

function ChangePasswordSection() {
  const [ancien, setAncien] = useState('');
  const [nouveau, setNouveau] = useState('');
  const [confirmer, setConfirmer] = useState('');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuccess(''); setError('');
    if (nouveau !== confirmer) { setError('Les mots de passe ne correspondent pas.'); return; }
    if (nouveau.length < 8) { setError('Le nouveau mot de passe doit contenir au moins 8 caractères.'); return; }
    setSaving(true);
    try {
      await api.changePassword(ancien, nouveau);
      setSuccess('Mot de passe modifié avec succès.');
      setAncien(''); setNouveau(''); setConfirmer('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur lors du changement de mot de passe');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface-container-low rounded-2xl border border-outline-variant p-6 space-y-4 mt-6">
      <h2 className="font-headline font-bold text-lg text-on-surface">Changer le mot de passe</h2>
      {success && <div className="p-3 bg-green-50 border border-green-200 text-green-700 text-sm rounded-xl flex items-center gap-2"><span className="material-symbols-outlined text-base">check_circle</span>{success}</div>}
      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl flex items-center gap-2"><span className="material-symbols-outlined text-base">error</span>{error}</div>}
      <div>
        <label className="block text-sm font-semibold text-on-surface mb-1.5">Mot de passe actuel</label>
        <input type="password" value={ancien} onChange={(e) => setAncien(e.target.value)} required
          className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary" />
      </div>
      <div>
        <label className="block text-sm font-semibold text-on-surface mb-1.5">Nouveau mot de passe</label>
        <input type="password" value={nouveau} onChange={(e) => setNouveau(e.target.value)} required
          className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary" />
      </div>
      <div>
        <label className="block text-sm font-semibold text-on-surface mb-1.5">Confirmer le nouveau mot de passe</label>
        <input type="password" value={confirmer} onChange={(e) => setConfirmer(e.target.value)} required
          className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary" />
      </div>
      <button type="submit" disabled={saving} className="btn-primary disabled:opacity-60">
        <span className="material-symbols-outlined text-xl">{saving ? 'progress_activity' : 'lock'}</span>
        {saving ? 'Modification…' : 'Modifier le mot de passe'}
      </button>
    </form>
  );
}

export default function ProfilEntreprise() {
  const [profil, setProfil] = useState<EntrepriseProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const [nomEntreprise, setNomEntreprise] = useState('');
  const [secteur, setSecteur] = useState('');
  const [ville, setVille] = useState('');
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const logoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.getMonEntreprise()
      .then((e) => {
        setProfil(e);
        setNomEntreprise(e.nom_entreprise ?? '');
        setSecteur(e.secteur ?? '');
        setVille(e.ville ?? '');
        setLogoUrl(e.logo_url ?? null);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setSuccess(''); setError('');
    try {
      const updated = await api.updateMonEntreprise({
        nom_entreprise: nomEntreprise || undefined,
        secteur: secteur || undefined,
        ville: ville || undefined,
      }) as EntrepriseProfile;
      setProfil(updated);
      setNomEntreprise(updated.nom_entreprise ?? '');
      setSecteur(updated.secteur ?? '');
      setVille(updated.ville ?? '');
      setSuccess('Profil mis à jour avec succès.');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-on-surface-variant">
        <span className="material-symbols-outlined animate-spin text-3xl">progress_activity</span>
      </div>
    );
  }

  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-10 pt-6 lg:pt-8 pb-12">
      <div className="max-w-2xl mx-auto">
        <h1 className="font-headline font-extrabold text-3xl text-on-surface mb-1">Mon profil entreprise</h1>
        <p className="text-on-surface-variant text-sm mb-8">Informations visibles par les étudiants et le club EnimConnect</p>

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-xl text-sm flex items-center gap-2">
            <span className="material-symbols-outlined text-green-600 text-base">check_circle</span>
            {success}
          </div>
        )}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm flex items-center gap-2">
            <span className="material-symbols-outlined text-red-600 text-base">error</span>
            {error}
          </div>
        )}

        {/* Status badge */}
        <div className="mb-6 flex items-center gap-3">
          {profil?.valide ? (
            <span className="flex items-center gap-1.5 text-sm font-semibold text-green-700 bg-green-50 border border-green-200 px-3 py-1.5 rounded-xl">
              <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>verified</span>
              Compte validé — vous pouvez publier des offres
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-sm font-semibold text-orange-700 bg-orange-50 border border-orange-200 px-3 py-1.5 rounded-xl">
              <span className="material-symbols-outlined text-base">hourglass_top</span>
              En attente de validation par le club EnimConnect
            </span>
          )}
        </div>

        {/* Logo upload */}
        <div className="bg-surface-container-low rounded-2xl border border-outline-variant p-6 mb-6">
          <h2 className="font-headline font-bold text-lg text-on-surface mb-4">Logo de l'entreprise</h2>
          <div className="flex items-center gap-5">
            <div className="w-20 h-20 rounded-2xl bg-primary/10 border border-outline-variant flex items-center justify-center overflow-hidden flex-shrink-0">
              {logoUrl ? (
                <img src={`${api.apiBase}${logoUrl}?t=${Date.now()}`} alt="Logo" className="w-full h-full object-cover" />
              ) : (
                <span className="material-symbols-outlined text-3xl text-on-surface-variant">business</span>
              )}
            </div>
            <div>
              <p className="text-sm text-on-surface-variant mb-3">
                {logoUrl ? 'Votre logo est visible par les étudiants.' : 'Ajoutez un logo pour être plus visible auprès des étudiants.'}
              </p>
              <input
                ref={logoInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setUploadingLogo(true);
                  setError('');
                  try {
                    const res = await api.uploadLogo(file);
                    setLogoUrl(res.logo_url);
                    setSuccess('Logo mis à jour avec succès.');
                  } catch (err: unknown) {
                    setError(err instanceof Error ? err.message : "Erreur lors de l'upload du logo");
                  } finally {
                    setUploadingLogo(false);
                    if (logoInputRef.current) logoInputRef.current.value = '';
                  }
                }}
              />
              <button
                type="button"
                onClick={() => logoInputRef.current?.click()}
                disabled={uploadingLogo}
                className="flex items-center gap-2 px-4 py-2 border border-primary text-primary text-sm font-semibold rounded-xl hover:bg-primary/5 transition-colors disabled:opacity-60"
              >
                <span className="material-symbols-outlined text-base">{uploadingLogo ? 'progress_activity' : 'upload'}</span>
                {uploadingLogo ? 'Upload…' : logoUrl ? 'Changer le logo' : 'Ajouter un logo'}
              </button>
            </div>
          </div>
        </div>

        <form onSubmit={handleSave} className="bg-surface-container-low rounded-2xl border border-outline-variant p-6 space-y-5">
          <h2 className="font-headline font-bold text-lg text-on-surface">Informations de l'entreprise</h2>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">
              Email <span className="font-normal text-on-surface-variant">(non modifiable)</span>
            </label>
            <input
              value={profil?.email ?? ''}
              disabled
              className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface-container text-on-surface-variant cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">
              Nom de l'entreprise <span className="text-error">*</span>
            </label>
            <input
              value={nomEntreprise}
              onChange={(e) => setNomEntreprise(e.target.value)}
              required
              placeholder="Ex. OCP Group"
              className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1.5">Secteur d'activité</label>
              <input
                value={secteur}
                onChange={(e) => setSecteur(e.target.value)}
                placeholder="Ex. Mines & Énergie"
                className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1.5">Ville</label>
              <input
                value={ville}
                onChange={(e) => setVille(e.target.value)}
                placeholder="Ex. Rabat"
                className="w-full border border-outline-variant rounded-xl px-4 py-2.5 text-sm bg-surface outline-none focus:border-primary"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="btn-primary flex-1 justify-center disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-xl">
                {saving ? 'progress_activity' : 'save'}
              </span>
              {saving ? 'Enregistrement…' : 'Enregistrer les modifications'}
            </button>
          </div>
        </form>

        <ChangePasswordSection />
      </div>
    </main>
  );
}
