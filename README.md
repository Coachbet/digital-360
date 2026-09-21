# adgi360 — Portail

Portail web interne de l'agence adgi360.

- `Portail-front end/` — React + TypeScript + Vite + Tailwind
- `Portail-backend/` — FastAPI (architecture DDD)
- `docker-compose.yml` — PostgreSQL + MinIO en local

Voir `CLAUDE.md` pour le contexte complet du projet.

## Démarrage rapide

```bash
docker compose up -d                                  # infra

cd Portail-backend                                     # terminal 1
source ~/.venvs/adgi360-backend/bin/activate
pip install -e ".[dev]" && cp .env.example .env
uvicorn adgi360.main:app --reload --app-dir src --port 8001

cd "Portail-front end"                                 # terminal 2
npm install && npm run dev
```

Portail sur http://localhost:5173 · API sur http://localhost:8001/docs · MinIO sur http://localhost:9001

## Données de démonstration

Depuis `Portail-backend`, avec l'environnement virtuel activé :

```bash
python scripts/seed_demo.py
```

Le script peut être relancé sans doublons. Il alimente uniquement l'agence de
test et crée clients, fichiers CSV, rapports PowerPoint, événements et factures PDF.
