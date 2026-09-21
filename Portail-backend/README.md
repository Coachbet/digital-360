# adgi360 — Portail (Backend)

API FastAPI en architecture DDD. Voir `CLAUDE.md` pour le contexte complet.

## Démarrer

```bash
# Depuis la racine du projet : docker compose up -d
source ~/.venvs/adgi360-backend/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn adgi360.main:app --reload --app-dir src --port 8001
```

- API : http://localhost:8001
- Doc interactive : http://localhost:8001/docs
- État des dépendances : http://localhost:8001/api/v1/health

## Modules

- **Clients** — référentiel des clients de l'agence
- **Données** — fichiers sources dans MinIO, rangés par client puis par période
- **Auto Review** — lancement du workflow n8n, suivi et validation humaine des rapports
- **Calendrier** — événements internes + synchro Google Calendar (lecture seule)
