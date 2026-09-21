# adgi360 — Contexte projet

## Quoi
Portail web interne pour **adgi360**, agence de marketing digital. Deux applications séparées qui communiquent via une API :

- **Frontend** : `Portail-front end/` — React + TypeScript + Vite + Tailwind (voir son `CLAUDE.md`)
- **Backend** : `Portail-backend/` — FastAPI en DDD (voir son `CLAUDE.md`)

Ce fichier est le contexte général à lire en premier.

## Emplacement
Le projet vit dans `~/Documents/adgi360` (déplacé hors de OneDrive : la synchro de `node_modules` et `.venv` provoquait des blocages).

## Stack

| Couche | Techno | Notes |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS | Organisation par *features*, composants UI maison façon shadcn |
| Backend | Python 3.11+ + FastAPI | Architecture DDD : `domain` / `application` / `infrastructure` / `interfaces` |
| Base de données | PostgreSQL 16 (Docker) | SQLAlchemy 2 async + asyncpg |
| Stockage fichiers | MinIO (Docker), API compatible S3 | Bucket `adgi360-files`, migration vers un vrai S3 sans changer le code |
| Automatisation | n8n + Ollama, en local | n8n analyse les données via l'IA, le backend produit le PowerPoint |
| Dépôts | 2 repos Git séparés (FE et BE), privés, sur le compte GitHub personnel | Pas encore fait |

## Démarrer le projet

```bash
# 1. Infra (à la racine du projet)
docker compose up -d

# 2. Backend
cd Portail-backend
source ~/.venvs/adgi360-backend/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn adgi360.main:app --reload --app-dir src --port 8001

# 3. Frontend (autre terminal)
cd "Portail-front end"
npm install
npm run dev
```

- Portail : http://localhost:5173
- API + doc interactive : http://localhost:8001/docs
- Console MinIO : http://localhost:9001 (adgi360 / adgi360secret)
- État des dépendances : http://localhost:8001/api/v1/health

Le venv Python est volontairement hors du projet (`~/.venvs/adgi360-backend`).

## Modules du portail

### 1. Données (`/data`)
Gestion des fichiers sources, **organisés par client puis par période** (`clients/<client_id>/<période>/<fichier>` dans MinIO). C'est le préalable à l'auto-review : on dépose ici, on sélectionne ensuite.

### 2. Auto Review (`/auto-review`)
Le flux complet :

1. L'utilisateur choisit un client, un **type de client** (liste fixe : e-commerce, B2B, lead gen, marketplace, local, marque, autre), coche les **fichiers sources** déjà déposés dans le module Données, et ajoute des infos complémentaires.
2. Le backend crée une `ReviewRequest` et appelle le **webhook n8n** avec le contexte, les clés MinIO des fichiers et une **URL de rappel**.
3. n8n télécharge les fichiers, en extrait les données, en fait un **résumé compact** (colonnes, totaux, échantillon) et le soumet à l'**IA locale Ollama**, qui rédige le plan du rapport en JSON.
4. n8n renvoie ce plan au backend sur `POST /api/v1/auto-review/{id}/render`. Le **backend génère le PowerPoint** aux couleurs adgi360 avec `python-pptx`, l'archive dans MinIO et bascule la review en « à relire ».
5. Un **humain relit et valide** dans le portail. Le rapport devient téléchargeable. **Aucun mail n'est envoyé** — c'est un humain qui décide de la suite.

Statuts : `pending` → `processing` → `awaiting_approval` → `approved` (ou `failed`).

**Pourquoi le backend génère le PPTX et pas n8n** : n8n n'a pas de nœud PowerPoint, alors que le backend est déjà en Python. n8n se concentre sur l'orchestration et l'appel à l'IA, le backend sur la mise en forme. Le design du deck peut ainsi évoluer sans toucher au workflow, et le prompt sans toucher au rendu.

Trois mises en page sont disponibles (`kpis`, `bullets`, `recommendations`), plus une couverture et une page de fin ajoutées automatiquement. Chaque champ manquant dans la réponse du modèle a une valeur de repli : un rapport imparfait vaut mieux qu'une génération en échec.

### 3. Calendrier (`/calendrier`)
Quatre usages : échéances de rapports, planning de campagnes, rendez-vous clients, planning interne. Synchro **Google Calendar en lecture seule** (Google Workspace est l'outil de l'équipe ; Outlook n'est pas concerné). Le client Google est en place mais l'authentification reste à configurer — le calendrier interne fonctionne sans.

### 4. Facturation (`/facturation`)
Saisie des prestations (client, lignes, remise, devise, régime de taxes) → le backend calcule les montants et génère un **PDF aux couleurs adgi360** avec ReportLab, archivé dans MinIO sous `invoices/<id>/`.

- Numérotation séquentielle par année : `ADGI-2026-0001`.
- Devises : CAD (défaut), USD, EUR. Régimes : Québec (TPS 5 % + TVQ 9,975 %), Canada (TPS seule), France (TVA 20 %), hors taxes.
- Les montants sont **figés en base à l'émission** : une facture archivée ne change pas si les taux évoluent.
- Une page « Coordonnées de l'agence » permet de saisir raison sociale, adresse, numéros TPS/TVQ et coordonnées de paiement, et de téléverser le logo. Les mentions légales absentes du site sont initialisées à **« À compléter »** — rien n'est inventé, il faut les renseigner avant d'envoyer une vraie facture. Sans logo, le PDF affiche un monogramme typographique ADIGI360.

### 5. Reporting
Prévu, pas encore développé (carte grisée sur l'accueil).

## Design
Charte inspirée du site adigi360.com : **accent magenta/rose sur fond clair**, typo Inter. Les tokens de couleur sont dans `Portail-front end/src/app/global.css` (variables CSS en HSL) et exposés à Tailwind via `tailwind.config.js`. Page d'accueil : un gros bloc arrondi par application.

## Authentification
**Aucune pour l'instant** (2-3 utilisateurs internes, tout en local). La structure est prête à en accueillir une : côté front tous les appels passent par `src/shared/api/client.ts`, côté back il suffira d'ajouter une dépendance FastAPI.

## Décisions prises
- FastAPI plutôt que Django/Flask : léger, async, adapté au DDD.
- Vite plutôt que Create React App.
- n8n orchestre et appelle l'IA locale (Ollama) ; le backend génère le PowerPoint avec python-pptx.
- Aucun envoi de mail : le rapport validé se télécharge depuis le portail. Gmail a été retiré de la chaîne.
- Synchro Google en lecture seule pour éviter tout risque sur les agendas de l'équipe.
- Projet sorti de OneDrive.

## Reste à faire
- [ ] Configurer l'authentification Google Calendar (compte de service ou OAuth2)
- [ ] Affiner le prompt de l'analyse IA selon le format réel des exports (nœud « Analyse IA » du workflow)
- [ ] Renseigner les coordonnées légales de l'agence dans la page Facturation (numéros TPS/TVQ « À compléter »)
- [ ] Migrations Alembic (aujourd'hui : `create_all` au démarrage, suffisant en dev)
- [ ] Module Reporting
- [ ] Authentification du portail
- [ ] Init Git + 2 repos privés sur GitHub
- [ ] Choix d'hébergement

## Contrat d'appel backend → n8n

Le backend envoie un POST sur `N8N_WEBHOOK_URL` :

```json
{
  "review_id": "uuid",
  "client": { "id": "uuid", "name": "Acme", "contact_email": "..." },
  "client_type": "ecommerce",
  "client_type_label": "E-commerce",
  "additional_info": "texte libre",
  "source_files": [
    { "id": "uuid", "filename": "export.xlsx", "storage_key": "clients/<id>/2026-09/export.xlsx", "period": "2026-09" }
  ],
  "render_callback_url": "http://host.docker.internal:8001/api/v1/auto-review/<review_id>/render"
}
```

n8n répond immédiatement, travaille en arrière-plan, puis rappelle `render_callback_url` avec le plan du rapport :

```json
{
  "title": "Rapport de performance — Acme",
  "subtitle": "Septembre 2026",
  "slides": [
    { "layout": "kpis", "title": "Chiffres clés", "kpis": [{ "label": "ROAS", "value": "4,8x", "delta": "+0,6" }] },
    { "layout": "bullets", "title": "Analyse", "bullets": ["..."] },
    { "layout": "recommendations", "title": "Recommandations", "items": [{ "title": "...", "detail": "..." }] }
  ]
}
```

Voir `n8n/README.md` pour l'import du workflow et le téléchargement du modèle Ollama.
