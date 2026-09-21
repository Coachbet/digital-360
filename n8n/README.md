# Workflows n8n pour le VPS Digital 360

## Importation
Dans n8n sur le VPS, créer un workflow puis menu ⋯ > Import from File.
Importer séparément :
- `0-test-ollama-vps.json` : lancer Execute Workflow, vérifier le champ response.
- `1-adgi360-auto-review.json` : enregistrer puis publier/activer.
Ne publier qu'un seul workflow utilisant le chemin POST `auto-review`.

## Configuration
Aucun credential n8n à ajouter : Ollama est joint à http://ollama:11434,
MinIO utilise les URL temporaires signées et le rappel backend porte un jeton HMAC.
Le modèle attendu est llama3.2:3b.
Le backend doit définir N8N_WEBHOOK_URL=http://n8n:5678/webhook/auto-review.

## Premier essai
Créer un client dans le portail, déposer un export Excel .xlsx avec une ligne
d'en-têtes puis des lignes de données, sélectionner ce fichier dans Rapports
et lancer la génération. Suivre l'exécution dans n8n > Executions.
Le backend génère ensuite le PPTX et affiche « À relire ».

Cette version accepte seulement les fichiers .xlsx (première feuille par défaut).
Elle transmet au modèle un échantillon plafonné à 30 lignes et 30 colonnes,
sans calcul de totaux sur la période. Ce n'est pas une analyse exhaustive.
Les régies publicitaires et les autres formats ne sont pas raccordés à ce flux.
Le workflow utilise les adresses Docker du VPS et ne convient pas tel quel
à une instance n8n Cloud.

## Erreurs
Une réponse IA invalide arrête l'exécution, sans produire un faux rapport.
Consulter le nœud rouge dans Executions. Le backend ne possède pas encore
de rappel d'échec : une review peut rester en processing si n8n échoue.
Après correction, lancer une nouvelle review depuis le portail.
Ne pas publier de captures contenant les URL signées ou le token de rappel.

## Déploiement de la correction backend
AutoReviewCreate accepte désormais client_type avec la valeur par défaut other :
le formulaire actuel n'envoie pas ce champ, mais le routeur en a besoin.
Publier les modifications Git puis, sur le VPS, faire git pull et :
```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d --build backend
```

## Validation
Les fichiers JSON et le code des nœuds sont vérifiés localement.
La validation de bout en bout nécessite l'import dans votre instance n8n
et un lancement réel depuis le portail.
