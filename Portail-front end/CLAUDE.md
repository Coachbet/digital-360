# Portail-front end — Contexte technique

> Contexte général : voir `../CLAUDE.md`.

## Stack
React 18 · TypeScript · Vite · Tailwind CSS · react-router-dom · date-fns · lucide-react

```bash
npm install
npm run dev     # http://localhost:5173
npm run build   # vérifie les types puis build
```

Les appels `/api/*` sont relayés vers `http://localhost:8001` par le proxy Vite — le backend doit tourner en parallèle.

## Organisation : par features

```
src/
  app/global.css          Tokens de couleur (variables CSS HSL) + directives Tailwind
  pages/Home.tsx          Accueil : un gros bloc arrondi par application
  features/
    clients/api.ts
    data/                 Dépôt et gestion des fichiers par client/période
    auto-review/          Formulaire de lancement + liste des rapports à valider
    calendar/             Calendrier mensuel + création d'événements
  shared/
    api/client.ts         Point d'entrée UNIQUE de tous les appels API
    components/
      AppLayout.tsx        Barre latérale + PageHeader
      AppCard.tsx          Le gros bloc « application » de l'accueil
      ui/                  Button, Card, Field, Badge (façon shadcn, sans dépendance)
    lib/utils.ts          cn() et formatBytes()
```

L'alias `@/` pointe vers `src/` (configuré dans `vite.config.ts` et `tsconfig.json`).

## Design

Charte inspirée du site adigi360.com : accent **magenta/rose** sur fond clair, typo Inter.

Les couleurs sont définies **une seule fois**, en HSL, dans `src/app/global.css` (`--primary`, `--background`, etc.) et exposées à Tailwind via `tailwind.config.js`. Pour changer la charte, il suffit de modifier ces variables — ne pas écrire de couleurs en dur dans les composants. Un mode sombre pourrait être ajouté en redéfinissant ces mêmes variables.

## Conventions

- Chaque feature a son `api.ts` qui utilise `shared/api/client.ts` — ne jamais appeler `fetch` directement dans un composant.
- Les composants `ui/` sont génériques et sans logique métier.
- Ajouter un module = un dossier dans `features/`, une route dans `App.tsx`, une entrée dans `NAV` (`AppLayout.tsx`) et une carte dans `pages/Home.tsx`.

## Points d'attention

- **Polling** : la page Auto Review interroge l'API toutes les 10 s pour voir arriver les rapports produits par n8n. À remplacer par du websocket/SSE si le besoin de réactivité augmente.
- **Pas d'authentification** pour l'instant. Quand elle arrivera, tout passera par `shared/api/client.ts` (en-tête Authorization, gestion du 401) sans toucher aux features.
- **Pas de librairie de state management** : `useState`/`useEffect` suffisent à ce stade. Si les appels se multiplient, envisager TanStack Query.

## Reste à faire
- Écran de gestion des clients (aujourd'hui les clients se créent via l'API `/api/v1/clients`)
- Module Reporting
- Logo adgi360 (actuellement un monogramme « a »)
- Responsive mobile de la barre latérale (masquée sous `md`)
