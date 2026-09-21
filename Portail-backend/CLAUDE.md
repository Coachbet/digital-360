# Portail-backend — Contexte technique

> Contexte général : voir `../CLAUDE.md`.

## Stack
Python 3.11+ · FastAPI · SQLAlchemy 2 (async, asyncpg) · PostgreSQL 16 · boto3 (MinIO/S3) · httpx (n8n)

## Démarrer

```bash
source ~/.venvs/adgi360-backend/bin/activate   # venv hors du projet
pip install -e ".[dev]"
cp .env.example .env
uvicorn adgi360.main:app --reload --app-dir src --port 8001
```

Docker (`docker compose up -d` à la racine) doit tourner : PostgreSQL sur 5432, MinIO sur 9000/9001. `GET /api/v1/health` indique l'état des deux.

## Architecture DDD

```
src/adgi360/
  domain/            # Cœur métier pur — aucune dépendance FastAPI/DB/S3/n8n
    auto_review/       ClientType, ReviewStatus, ReviewRequest
    calendar/          EventCategory, EventSource, CalendarEvent
    data/              DataFile + conventions de clés de stockage
  application/       # Cas d'usage : orchestrent domaine + infrastructure
    auto_review/use_cases/
      launch_auto_review.py   valide et déclenche n8n
      sync_reports.py         détecte les PPT déposés par n8n dans MinIO
      approve_review.py       validation humaine
  infrastructure/    # Implémentations concrètes
    db/                modèles SQLAlchemy, session, init_db
    storage/           client S3/MinIO (boto3, appels déportés en thread)
    n8n/               client webhook
    calendar_sync/     client Google Calendar (lecture seule, à configurer)
    config/            settings pydantic
  interfaces/api/v1/ # Endpoints FastAPI + schémas Pydantic
    routers/           health, clients, data, auto_review, calendar
```

Règle : le `domain/` n'importe jamais rien de `infrastructure/`. Les routers ne contiennent pas de logique métier, ils appellent des cas d'usage.

## Endpoints

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/api/v1/health` | État DB + stockage |
| GET/POST | `/api/v1/clients` | Liste / création de clients |
| GET/DELETE | `/api/v1/clients/{id}` | Détail / suppression |
| GET | `/api/v1/data/clients/{id}/periods` | Périodes d'un client + nb de fichiers |
| GET/POST | `/api/v1/data/files` | Liste / upload (multipart, multi-fichiers) |
| GET | `/api/v1/data/files/{id}/download` | URL présignée |
| DELETE | `/api/v1/data/files/{id}` | Suppression (base + MinIO) |
| GET | `/api/v1/auto-review/client-types` | Liste fixe des types de clients |
| GET/POST | `/api/v1/auto-review` | Liste (avec sync n8n) / lancement |
| POST | `/api/v1/auto-review/{id}/approve` | Validation humaine |
| GET | `/api/v1/auto-review/{id}/report` | URL présignée du PPT |
| GET | `/api/v1/calendar/categories` | Catégories d'événements |
| GET/POST | `/api/v1/calendar/events` | Liste / création |
| DELETE | `/api/v1/calendar/events/{id}` | Suppression |

## Points d'attention

- **Migrations** : aujourd'hui `Base.metadata.create_all()` au démarrage. Suffisant en dev, à remplacer par Alembic avant toute mise en production.
- **boto3 est synchrone** : tous les appels passent par `asyncio.to_thread` pour ne pas bloquer la boucle événementielle.
- **Détection des rapports** : n8n ne prévient pas le backend. `SyncReportsUseCase` scanne `reports/<review_id>/` à chaque listing des reviews. Si le volume augmente, passer à un callback n8n → backend.
- **Démarrage tolérant** : si Docker n'est pas lancé, l'API démarre quand même (warning dans les logs) pour que `/health` reste consultable.
- **Ajouter un type de client** : ajouter une valeur à `ClientType` dans `domain/auto_review/entities.py` et son libellé — le frontend la récupère automatiquement.

## Reste à faire
- Authentification Google Calendar (`infrastructure/calendar_sync/google_calendar.py` : `is_configured()` renvoie False tant que rien n'est configuré, le calendrier interne fonctionne sans)
- Alembic
- Authentification du portail
- Tests (`tests/unit`, `tests/integration` sont vides)
