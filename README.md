# EnimConnect — Plateforme de mise en relation étudiants-entreprises

Plateforme intelligente pour l'École Nationale Supérieure des Mines de Rabat (ENSMR) qui digitalise le processus de recherche de stage avec un moteur de matching IA.

---

## Stack technique

| Couche | Technologie |
|---|---|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS v4 |
| Backend | FastAPI + Python 3.11+ |
| Base de données | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2 + Alembic |
| IA — LLM | OpenAI gpt-4o-mini (extraction structurée des CV) |
| IA — Embeddings | OpenAI text-embedding-3-small (vecteurs 1536D) |
| IA — Matching | Similarité cosinus via pgvector |
| PDF | PyMuPDF (extraction texte) |
| Auth | JWT HS256 (access 30min + refresh 7j) |
| Liens email | HMAC-SHA256 (validation 48h, reset mdp 1h) |
| Email | SMTP direct (réinitialisation mdp) + N8n (notifications chefs/entreprises) |
| Stockage fichiers | Local ou Amazon S3 (abstraction configurable) |
| Automation | N8n (workflow validation annonces par email) |
| Déploiement | Docker Compose + Nginx reverse proxy + Let's Encrypt |

---

## Architecture

```
projetFederateur/
├── backend/                     # FastAPI
│   ├── app/
│   │   ├── main.py              # Application + CORS + routes statiques
│   │   ├── config.py            # Variables d'env via pydantic-settings
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── limiter.py           # Rate limiting (slowapi)
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py          # Users (etudiant/entreprise/club)
│   │   │   ├── etudiant.py      # Profil étudiant
│   │   │   ├── entreprise.py    # Profil entreprise (+ logo)
│   │   │   ├── annonce.py       # Offres de stage
│   │   │   ├── annonce_validation_dept.py  # Validation par département
│   │   │   ├── cv.py            # CVs + données IA
│   │   │   ├── candidature.py   # Candidatures
│   │   │   ├── chef_departement.py  # Chefs de département
│   │   │   └── notification.py  # Notifications in-app
│   │   ├── schemas/             # Pydantic schemas (validation E/S)
│   │   ├── routers/             # Endpoints FastAPI
│   │   │   ├── auth.py          # /auth/* (login, register, reset mdp)
│   │   │   ├── etudiants.py     # /etudiants/* + /api/cv/*
│   │   │   ├── annonces.py      # /annonces/* (tri IA)
│   │   │   ├── entreprises.py   # /entreprises/* (logo, offres, candidats)
│   │   │   ├── club.py          # /club/* (admin complet)
│   │   │   ├── validation.py    # /decision/* + /valider-dept/* + /rejeter-dept/*
│   │   │   └── notifications.py # /notifications/*
│   │   ├── services/
│   │   │   ├── auth_service.py       # bcrypt + JWT
│   │   │   ├── cv_service.py         # PyMuPDF + GPT-4o-mini
│   │   │   ├── embedding_service.py  # OpenAI embeddings
│   │   │   ├── matching_service.py   # Cosine similarity pgvector
│   │   │   ├── storage_service.py    # Abstraction local/S3
│   │   │   ├── email_service.py      # SMTP transactionnel
│   │   │   ├── n8n_service.py        # Webhooks N8n
│   │   │   ├── token_service.py      # HMAC-SHA256 liens signés
│   │   │   └── notification_service.py # Notifications in-app
│   │   ├── tasks/
│   │   │   ├── analyze_cv.py         # Background: PDF → IA → embedding
│   │   │   └── embed_annonce.py      # Background: annonce → embedding
│   │   └── middleware/
│   │       └── auth_middleware.py     # JWT dependencies FastAPI
│   ├── alembic/                 # Migrations (001→008)
│   ├── storage/                 # Fichiers uploadés (cvs/, photos/, logos/)
│   ├── requirements.txt
│   └── .env.example
├── Enim_Connect_Website/        # Frontend React
│   ├── src/
│   │   ├── api/client.ts        # Couche API centralisée (refresh token auto)
│   │   ├── context/AuthContext.tsx
│   │   ├── constants/ensmr.ts   # Départements, filières, niveaux ENSMR
│   │   ├── pages/
│   │   │   ├── auth/            # Login, Register, Reset Password, ForceChangePassword
│   │   │   ├── student/         # Dashboard, Recherche, Candidatures, Profil
│   │   │   ├── company/         # Dashboard, Offres, Candidats, Profil
│   │   │   ├── admin/           # Entreprises, Offres (+ demandes suppression), Étudiants, Stats
│   │   │   └── DecisionPage.tsx # Interface chef de département
│   │   └── components/
│   │       ├── layout/          # Layouts avec auth guard par rôle
│   │       ├── CandidateDetail.tsx  # Fiche candidat (IA + CV + contact)
│   │       └── SideNavBar.tsx   # Navigation latérale
│   └── .env.example
├── docker-compose.yml           # Dev local
└── docker-compose.prod.yml      # Production (nginx + SSL + N8n)
```

---

## Les 4 acteurs et leurs accès

| Acteur | Role JWT | Accès |
|---|---|---|
| Étudiant | `etudiant` | Profil, CV (upload + analyse IA), recherche d'offres triées par IA, candidatures, notifications |
| Entreprise | `entreprise` | Profil + logo, publication d'offres multi-département, consultation des candidats triés par IA, recherche étudiants |
| Club EnimConnect | `club` | Validation entreprises, gestion offres, gestion étudiants (CRUD + import CSV), statistiques, création de comptes |
| Chef de département | — (pas de compte) | Valide/rejette les annonces via liens email signés HMAC (48h) |

---

## Logique IA

### Pipeline CV (tâche background — ne bloque jamais l'UI)

```
Upload PDF → PyMuPDF (extraction texte)
           → GPT-4o-mini (description structurée 3-4 phrases)
           → text-embedding-3-small (vecteur 1536D)
           → Sauvegarde en base (description + embedding pgvector)
```

### Pipeline Annonce (tâche background — déclenchée à la validation)

```
Validation chef → text-embedding-3-small (embedding description)
               → Sauvegarde en base (embedding pgvector)
```

### Matching hybride cosinus

| Vue | Tri |
|---|---|
| Étudiant → liste d'offres | `cosinus(cv_embedding, annonce_embedding)` DESC |
| Entreprise → liste de candidats | `cosinus(annonce_embedding, cv_embedding)` DESC |

- Les **scores ne sont jamais exposés** dans les réponses API (vie privée)
- Les **compétences en correspondance** sont retournées pour l'explicabilité du matching
- Un étudiant ne voit que les offres **validées pour son département**

### Extraction structurée des CV

GPT-4o-mini extrait du texte brut du PDF :
- Description synthétique (affichée aux recruteurs)
- Compétences techniques détectées
- Données structurées (JSONB) pour le matching

---

## Système de validation multi-département

Chaque offre peut cibler **plusieurs départements**. La validation se fait indépendamment par département :

```
Entreprise publie offre (ex: GI + EM)
  │
  ├─ Création AnnonceValidationDept pour GI (statut: en_attente)
  │   └─ N8n envoie email au chef GI avec liens signés HMAC
  │       ├─ Lien "Valider" (GET, 1 clic)
  │       └─ Lien "Refuser" (formulaire avec motif)
  │
  └─ Création AnnonceValidationDept pour EM (statut: en_attente)
      └─ N8n envoie email au chef EM avec liens signés HMAC

Chef GI valide → offre visible pour étudiants GI + embedding généré
Chef EM rejette (motif) → offre invisible pour étudiants EM

Entreprise notifiée à chaque décision (in-app + email via N8n)
```

- Les liens HMAC expirent après **48 heures**
- Le premier chef qui clique verrouille la décision pour ce département
- Le club peut aussi valider/rejeter au niveau global

---

## Système de notifications

### Notifications in-app
- Stockées en base, affichées via icône cloche dans le header
- Tri : non lues en premier, puis par date décroissante (max 50)
- Actions : marquer comme lu, marquer tout lu, supprimer, supprimer tout

### Événements notifiés

| Événement | Destinataire |
|---|---|
| Nouvelle entreprise inscrite | Tous les membres du club |
| Entreprise validée/rejetée | L'entreprise concernée |
| Nouvelle offre soumise | Tous les membres du club |
| Offre validée/rejetée (par chef) | L'entreprise concernée |
| Nouveau candidat sur une offre | L'entreprise propriétaire |
| Demande de suppression d'offre | Tous les membres du club |
| Suppression approuvée/refusée | L'entreprise + les étudiants candidats |

### Notifications email (via N8n)
- Email aux chefs de département avec liens de décision
- Email à l'entreprise avec le résumé de la décision par département

---

## Stockage des fichiers

### Architecture dual-mode

Le stockage est configurable via `STORAGE_BACKEND` (`local` ou `s3`) :

| Type | Local | S3 |
|---|---|---|
| CVs | `./storage/cvs/{etudiant_id}.pdf` | `s3://{bucket}/cvs/{etudiant_id}.pdf` |
| Photos | `./storage/photos/{user_id}.{ext}` | — (local uniquement) |
| Logos | `./storage/logos/{entreprise_id}.{ext}` | — (local uniquement) |

- **CVs** : servis via endpoint protégé `/api/cv/{id}` (JWT requis, contrôle d'accès par rôle)
- **Photos** : servis via `/api/photos/{id}` (endpoint dédié)
- **Logos** : servis via `/api/logos/{id}` (endpoint dédié)
- En mode S3 : les fichiers sont streamés à travers le backend (évite les problèmes CORS)

### Contraintes d'upload

| Type | Formats | Taille max | Validation |
|---|---|---|---|
| CV | PDF uniquement | 10 Mo | Content-Type + octets magiques `%PDF-` |
| Photo | JPEG, PNG, WebP | 5 Mo | Content-Type |
| Logo | JPEG, PNG, WebP | 5 Mo | Content-Type + taille vérifiée |

---

## API — Résumé des endpoints

### Auth (`/auth`)
```
POST /auth/register              {email, password, role}
POST /auth/login                 {email, password} → {access_token, refresh_token}
POST /auth/google                {credential} → Google OAuth @enim.ac.ma uniquement
POST /auth/refresh               {refresh_token} → {access_token}
POST /auth/logout
POST /auth/forgot-password       {email} → email avec lien de reset (1h)
POST /auth/reset-password        {token, nouveau_mot_de_passe}
PUT  /auth/change-password       {ancien_mot_de_passe, nouveau_mot_de_passe}
PUT  /auth/force-change-password {nouveau_mot_de_passe} → 1ère connexion obligatoire
```

### Étudiant (`/etudiants`, JWT rôle: etudiant)
```
GET  /etudiants/me
PUT  /etudiants/me
POST /etudiants/me/photo         (multipart, JPEG/PNG/WebP)
POST /etudiants/me/cv            (multipart, PDF + consentement IA)
GET  /etudiants/me/cv
GET  /etudiants/me/candidatures
GET  /api/cv/{etudiant_id}       (téléchargement CV, contrôle d'accès)
```

### Annonces (`/annonces`, JWT requis)
```
GET    /annonces                 (triées par IA si étudiant avec CV)
GET    /annonces/{id}
POST   /annonces/{id}/postuler   (CV requis)
DELETE /annonces/{id}/postuler   (retirer candidature)
```

### Entreprise (`/entreprises`, JWT rôle: entreprise)
```
GET  /entreprises/me
PUT  /entreprises/me
POST /entreprises/me/logo                      (multipart, max 5 Mo)
POST /entreprises/annonces                     (entreprise validée, multi-département)
GET  /entreprises/annonces
PUT  /entreprises/annonces/{id}                (si pas encore validée)
DELETE /entreprises/annonces/{id}
GET  /entreprises/annonces/{id}/candidatures   (triés par matching IA)
GET  /entreprises/recherche?departement=&niveau=
```

### Validation par département (liens signés HMAC, 48h)
```
GET  /api/decision/{validation_id}?token=&chef_id=      (JSON: infos offre)
POST /api/decision/{validation_id}                       (JSON: action + motif)
GET  /valider-dept/{validation_id}?token=&chef_id=       (1-clic approbation)
GET  /rejeter-form/{validation_id}?token=&chef_id=       (formulaire rejet)
POST /rejeter-dept/{validation_id}?token=&chef_id=       (soumet rejet + motif)
```

### Club admin (`/club`, JWT rôle: club)
```
# Entreprises
GET  /club/entreprises
PUT  /club/entreprises/{id}/valider
PUT  /club/entreprises/{id}/rejeter
PUT  /club/entreprises/{id}/reset-password
DELETE /club/entreprises/{id}
POST /club/entreprises/bulk-delete
POST /club/creer-entreprise
GET  /club/entreprises-avec-offres
GET  /club/entreprises/{id}/annonces

# Étudiants
GET  /club/etudiants
POST /club/creer-etudiant
PUT  /club/etudiants/{id}/reset-password
DELETE /club/etudiants/{id}
POST /club/etudiants/bulk-delete
POST /club/import-etudiants              (CSV: nom, prenom, email, filiere, niveau)

# Offres
GET  /club/annonces
PUT  /club/annonces/{id}/valider
PUT  /club/annonces/{id}/rejeter
PUT  /club/annonces/{id}/toggle-actif

# Demandes de suppression d'offres
GET  /club/demandes-suppression
PUT  /club/annonces/{id}/approuver-suppression
PUT  /club/annonces/{id}/rejeter-suppression

# Stats
GET  /club/stats
GET  /club/stats/etudiants
```

### Notifications (`/notifications`, JWT requis)
```
GET    /notifications
GET    /notifications/non-lues
POST   /notifications/{id}/lire
POST   /notifications/lire-tout
DELETE /notifications/{id}
DELETE /notifications              (supprimer toutes les notifications)
```

---

## Sécurité

### Authentification
- Mots de passe : **bcrypt** avec politique de force obligatoire (8+ chars, majuscule, minuscule, chiffre, caractère spécial)
- **Changement obligatoire** à la première connexion pour les comptes créés par l'admin (flag `must_change_password` + claim JWT `mcp`)
- JWT : HS256, access token 30min, refresh token 7j
- Refresh token ne retourne qu'un nouveau access token
- Recherche email insensible à la casse (login + reset)
- Google OAuth : réservé aux étudiants avec email `@enim.ac.ma`

### Rate limiting (slowapi)

| Endpoint | Limite |
|---|---|
| `POST /auth/register` | 5/heure |
| `POST /auth/login` | 10/minute |
| `POST /auth/google` | 10/minute |
| `POST /auth/forgot-password` | 3/heure |
| `POST /auth/reset-password` | 5/heure |
| `POST /etudiants/me/cv` | 3/heure |
| `GET /annonces` | 30/heure |

### Liens email signés
- Validation chef : HMAC-SHA256, expiration **48h**
- Réinitialisation mot de passe : HMAC-SHA256, expiration **1h**
- Réponse générique (ne révèle pas l'existence d'un compte)

### Contrôle d'accès
- CORS : uniquement `FRONTEND_URL`
- Entreprise non validée → 403 même avec JWT valide
- CV : étudiant (son propre CV), entreprise validée, club uniquement
- Score IA jamais exposé dans les réponses API
- Emails étudiants : validation du domaine `@enim.ac.ma` (création + import CSV)

### Validation fichiers
- CV : Content-Type `application/pdf` + octets magiques `%PDF-` + taille max 10 Mo
- Photos/Logos : Content-Type vérifié + taille max 5 Mo
- Header `X-Content-Type-Options: nosniff` sur les réponses fichier

---

## Installation

### Prérequis

- Python 3.11+
- Node.js 20+
- PostgreSQL 16 avec extension pgvector
- Clé API OpenAI
- N8n instance (optionnel pour le dev local)

### 1. PostgreSQL + pgvector

```bash
# Ubuntu/Debian
sudo apt install postgresql-16 postgresql-16-pgvector

# macOS
brew install postgresql pgvector

# Créer la base
psql -U postgres -c "CREATE DATABASE enimconnect;"
psql -U postgres -d enimconnect -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Backend

```bash
cd backend

# Environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Dépendances
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditez .env avec vos vraies valeurs

# Migrations
alembic upgrade head

# Lancer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd Enim_Connect_Website

npm install

cp .env.example .env.local
# Vérifiez que VITE_API_URL=http://localhost:8000

npm run dev
```

L'application est disponible sur `http://localhost:5173`

---

## Variables d'environnement — Backend

### Obligatoires

| Variable | Description | Exemple |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL | `postgresql://user:pass@localhost:5432/enimconnect` |
| `SECRET_KEY` | Clé JWT (min 32 chars) | `super-secret-key-here` |
| `HMAC_SECRET` | Secret HMAC liens email (min 32 chars) | `hmac-secret-here` |
| `OPENAI_API_KEY` | Clé API OpenAI | `sk-...` |
| `N8N_WEBHOOK_URL` | URL webhook N8n (validation chefs) | `http://localhost:5678/webhook/chef-validation` |

### Optionnelles

| Variable | Description | Défaut |
|---|---|---|
| `N8N_COMPANY_WEBHOOK_URL` | Webhook décision entreprise | `""` |
| `FRONTEND_URL` | URL frontend (CORS + liens email) | `https://enimconnect.duckdns.org` |
| `BACKEND_URL` | URL backend publique | `https://enimconnect.duckdns.org` |
| `STORAGE_PATH` | Répertoire stockage local | `./storage` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée access token | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Durée refresh token | `7` |

### Stockage S3 (si `STORAGE_BACKEND=s3`)

| Variable | Description | Défaut |
|---|---|---|
| `STORAGE_BACKEND` | `local` ou `s3` | `local` |
| `S3_BUCKET` | Nom du bucket | `""` |
| `AWS_REGION` | Région AWS | `eu-north-1` |
| `AWS_ACCESS_KEY_ID` | Clé d'accès AWS | `""` (IAM role si vide) |
| `AWS_SECRET_ACCESS_KEY` | Secret AWS | `""` (IAM role si vide) |
| `S3_PRESIGN_EXPIRE` | Durée URL présignées (secondes) | `300` |

### SMTP (emails transactionnels)

| Variable | Description | Défaut |
|---|---|---|
| `N8N_SMTP_HOST` | Serveur SMTP | `smtp.gmail.com` |
| `N8N_SMTP_PORT` | Port SMTP | `587` |
| `N8N_SMTP_USER` | Utilisateur SMTP | `""` |
| `N8N_SMTP_PASS` | Mot de passe SMTP | `""` |
| `N8N_SMTP_SENDER` | Adresse expéditeur | `noreply@enimconnect.ma` |
| `N8N_SMTP_SSL` | SSL direct (true) ou STARTTLS (false) | `false` |

### Emails chefs de département

| Variable | Description |
|---|---|
| `CHEF_INFO_EMAIL` | Chef Informatique |
| `CHEF_MAT_EMAIL` | Chef Mathématiques |
| `CHEF_EM_EMAIL` | Chef Électromécanique |
| `CHEF_GI_EMAIL` | Chef Génie Informatique |
| `CHEF_GPI_EMAIL` | Chef Génie des Procédés |
| `CHEF_ST_EMAIL` | Chef Sciences de la Terre |
| `CHEF_MINES_EMAIL` | Chef Mines |

---

## Déploiement — AWS + Docker + DuckDNS + Let's Encrypt

### Infrastructure

La plateforme est déployée sur une **instance AWS EC2** avec HTTPS automatique :

| Composant | Technologie | Rôle |
|---|---|---|
| Serveur | AWS EC2 (Ubuntu) | Hébergement de tous les services |
| DNS dynamique | DuckDNS | Domaine `enimconnect.duckdns.org` pointant vers l'IP publique EC2 |
| Certificat SSL | Let's Encrypt (Certbot) | HTTPS gratuit avec renouvellement automatique |
| Reverse proxy | Nginx | Terminaison SSL, routage frontend/backend/N8n |
| Conteneurisation | Docker Compose | Orchestration des 3 services |

### Architecture réseau

```
Client (navigateur)
    │
    │  HTTPS :443
    ▼
┌──────────────────────────────────────────────────────┐
│  AWS EC2                                             │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Nginx (conteneur frontend)                     │ │
│  │  - SSL termination (Let's Encrypt)              │ │
│  │  - Sert le build React statique                 │ │
│  │  - Reverse proxy vers backend & N8n             │ │
│  │  - Gzip + cache assets statiques (1 an)         │ │
│  │  - Redirection HTTP → HTTPS automatique         │ │
│  └─────┬────────────────────┬──────────────────────┘ │
│        │                    │                         │
│        │ /api, /auth,       │ /webhook/               │
│        │ /etudiants, ...    │                         │
│        ▼                    ▼                         │
│  ┌───────────┐       ┌───────────┐                   │
│  │  Backend   │       │    N8n    │                   │
│  │  FastAPI   │       │  :5678   │                   │
│  │  :8000     │       │ (interne)│                   │
│  └───────────┘       └───────────┘                   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Services Docker

| Service | Image | Ports | Volumes |
|---|---|---|---|
| `backend` | Python 3.11 + FastAPI | 8000 (interne) | `backend_storage` (CVs, photos, logos) |
| `frontend` | Node 20 (build) + Nginx (prod) | 80, 443 | `/etc/letsencrypt` (lecture seule) |
| `n8n` | n8nio/n8n:latest | 5678 (interne) | `n8n_data` |

Le frontend utilise un **multi-stage build** : Node.js compile le projet React/Vite, puis Nginx sert les fichiers statiques et agit comme reverse proxy.

### Configuration DuckDNS

DuckDNS fournit un sous-domaine gratuit qui pointe vers l'IP publique de l'instance EC2. Un cron job met à jour l'IP automatiquement :

```bash
# Cron toutes les 5 minutes pour mettre à jour l'IP DuckDNS
*/5 * * * * curl -s "https://www.duckdns.org/update?domains=enimconnect&token=VOTRE_TOKEN&ip=" > /dev/null
```

### Certificat SSL — Let's Encrypt

Le certificat HTTPS est généré via **Certbot** en mode standalone avant le premier déploiement :

```bash
# Installation de Certbot
sudo apt install certbot

# Génération du certificat (ports 80/443 doivent être libres)
sudo certbot certonly --standalone -d enimconnect.duckdns.org

# Le certificat est stocké dans /etc/letsencrypt/live/enimconnect.duckdns.org/
# - fullchain.pem (certificat + chaîne)
# - privkey.pem   (clé privée)
```

Le renouvellement est automatique via le timer systemd de Certbot. Nginx charge les certificats en lecture seule depuis le volume monté.

### Routage Nginx

| Chemin | Destination | Description |
|---|---|---|
| `/` | Build React statique | SPA avec fallback `index.html` |
| `/auth/*`, `/api/*`, `/etudiants/*`, ... | `backend:8000` | API FastAPI |
| `/storage/*` | `backend:8000` | Fichiers statiques (photos, logos) |
| `/webhook/*` | `n8n:5678` | Webhooks N8n (validation chefs) |

### Déploiement

Le script `deploy.sh` automatise tout le processus :

```bash
./deploy.sh
```

Il effectue les étapes suivantes :
1. `git pull origin main` — récupère le dernier code
2. `docker compose down` — arrête les services
3. `docker compose up -d --build` — rebuild et redémarre
4. Attend 15 secondes le démarrage du backend
5. `alembic upgrade head` — applique les migrations en attente
6. `seed_chefs.py` — met à jour les chefs de département

### Lancer manuellement

```bash
# Build et démarrage
docker compose -f docker-compose.prod.yml up -d --build

# Appliquer les migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Migrations Alembic

| Version | Description |
|---|---|
| 001 | Schéma initial (users, étudiants, entreprises, annonces, candidatures, CVs) |
| 002 | Système de notifications |
| 003 | Validation multi-département des annonces |
| 004 | Champs IA structurés + index HNSW pgvector pour le matching |
| 005 | Champ `logo_url` pour les entreprises |
| 006 | Champ `suppression_demandee` pour les annonces |
| 007 | Champ `must_change_password` pour les utilisateurs |
| 008 | Migration des URLs de stockage `/storage/` → `/api/` |
