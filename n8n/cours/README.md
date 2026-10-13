# Projet n8n — bot Telegram Digital 360 (version poste local)

Quatre workflows à importer dans n8n (menu ⋯ › Import from File), **dans cet ordre** :

| Fichier | Rôle |
|---|---|
| `2-adgi360-verifier-utilisateur.json` | Sous-workflow : reconnaît l'expéditeur Telegram (Postgres) et journalise l'accès |
| `4-adgi360-alertes-erreurs.json` | Error workflow : prévient l'administrateur sur Telegram |
| `1-adgi360-auto-review.json` | Analyse des exports + IA, avec retries, rappel d'échec et envoi du PPTX dans Telegram |
| `3-adgi360-bot-telegram.json` | Le bot : liaison par numéro, commandes, texte libre compris par l'IA |

`1-adgi360-auto-review.json` remplace le workflow « adgi360 Auto Review » actuel (même chemin
de webhook `auto-review`) : désactiver l'ancien avant d'activer celui-ci.

Les fichiers sont générés par `../build_cours.py` : modifier le script plutôt que les JSON.

## 1. Backend

Dans `Portail-backend/.env`, ajouter un secret partagé avec n8n :

```bash
BOT_API_TOKEN=$(openssl rand -hex 32)   # coller la valeur obtenue
```

Redémarrer uvicorn. Au démarrage, les colonnes `users.phone`, `users.telegram_user_id`,
`users.telegram_linked_at` et la table `bot_events` sont créées automatiquement
(pas besoin de réinitialiser la base).

Dans le portail, **Mon agence › Bot Telegram** : saisir le numéro de téléphone de votre
compte Telegram.

## 2. Credentials n8n (4)

| Nom (exactement) | Type | Valeurs |
|---|---|---|
| `adgi360 Bot` | Telegram API | jeton donné par @BotFather (`/newbot`) |
| `adgi360 Bot API` | Header Auth | Name `X-Bot-Token`, Value = `BOT_API_TOKEN` |
| `adgi360 Postgres` | Postgres | host `host.docker.internal`, port `5433`, base/utilisateur/mot de passe `adgi360` |
| `Ollama local` | Ollama | Base URL `http://host.docker.internal:11434` |

Après import, ouvrir chaque nœud marqué en rouge et choisir le credential dans la liste.

## 3. Branchements après import

1. Bot Telegram › nœud **Vérifier l'utilisateur** : choisir « adgi360 – Vérifier l'utilisateur ».
2. Alertes erreurs › nœud **Configuration** : remplacer `0` par votre chat_id Telegram
   (visible dans n'importe quelle exécution du bot : `message.chat.id`).
3. Bot Telegram et Auto Review › Settings › **Error workflow** : « adgi360 – Alertes erreurs ».
4. Activer les quatre workflows.

## 4. HTTPS pour le Telegram Trigger

Telegram n'envoie les messages qu'à une URL HTTPS publique. En local :

```bash
cloudflared tunnel --url http://localhost:5678
```

Recréer ensuite le conteneur n8n avec `WEBHOOK_URL=https://<sous-domaine>.trycloudflare.com/`
puis désactiver/réactiver le bot. L'URL change à chaque lancement du tunnel. Sur le VPS,
`https://${N8N_DOMAIN}` suffit.

## 5. Scénario de démo (5 minutes)

1. `/start` → le bot demande le numéro → **Partager mon numéro** → « Compte lié : … ».
2. `/clients` → liste des clients **de votre agence uniquement**.
3. « fais-moi le rapport de Maison Boréale pour septembre » → l'IA comprend la demande →
   « Rapport lancé ».
4. Quelques minutes plus tard : le PowerPoint arrive dans la conversation avec les KPI en
   légende. Dans le portail, la review est « À relire ».
5. `/statut` → la review apparaît.
6. **Panne** : arrêter uvicorn, envoyer `/statut` → 3 tentatives, puis « Portail
   indisponible » côté utilisateur et 🚨 alerte côté administrateur.
7. **Sécurité** : depuis un autre compte Telegram, transférer votre fiche contact au bot →
   refus (« contact d'une autre personne »).

Prérequis : un export `.xlsx` déposé pour le client (ex. `donnees-test/export-google-ads-DEMO-2026-09.xlsx`).

## Ce qui changerait sur WhatsApp

Le numéro de téléphone serait fourni directement par le webhook WhatsApp (`from`), la
liaison par bouton deviendrait inutile. En revanche, l'envoi du PPTX plusieurs minutes
après la demande reste dans la fenêtre de 24 h, mais une alerte proactive (hors fenêtre)
exigerait un modèle de message approuvé par Meta, et seuls les numéros testeurs déclarés
peuvent écrire au bot pendant le développement.
