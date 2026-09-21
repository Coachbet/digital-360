# adgi360 — Portail (Frontend)

React + TypeScript + Vite + Tailwind. Voir `CLAUDE.md` pour le contexte complet.

## Démarrer

```bash
npm install
npm run dev
```

http://localhost:5173 — les appels `/api/*` sont relayés vers le backend sur le port 8001, qui doit tourner en parallèle.

Copier `.env.example` vers `.env.local` seulement si le frontend doit appeler
un backend distant. En local, laisser `VITE_API_BASE_URL` vide.

## Déployer l'interface sur Vercel

Créer un projet Vercel dont le **Root Directory** est `Portail-front end`, puis
ajouter la variable d'environnement :

```text
VITE_API_BASE_URL=https://adresse-publique-du-backend
```

La valeur ne doit contenir ni `/api/v1` ni slash final. Le fichier
`vercel.json` assure que les routes React comme `/facturation` restent
accessibles après un rafraîchissement de page.

## Écrans

- **Accueil** — un gros bloc arrondi par application
- **Données** — dépôt et organisation des fichiers par client/période
- **Auto Review** — formulaire de lancement et validation des rapports générés
- **Calendrier** — vue mensuelle, création d'événements
