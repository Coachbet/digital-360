# Workflow n8n du portail adgi360

Un seul workflow à importer dans ton instance n8n locale (http://localhost:5678) : `1-adgi360-auto-review.json`.

**Aucun credential à créer.** Ni MinIO, ni Gmail, ni Ollama : tous les appels passent par HTTP sans authentification, sur ta machine.

## Importer

Dans n8n : menu **⋯** en haut à droite → **Import from File…** → sélectionne `1-adgi360-auto-review.json`. Puis **Publish** pour l'activer — un workflow inactif ne répond que sur une URL de test, et le backend recevrait une 404.

## Prérequis : le modèle Ollama

Le workflow appelle ton conteneur `n8n-ollama`. Le modèle doit être téléchargé une fois :

```bash
docker exec -it n8n-ollama ollama pull llama3.1
```

Pour changer de modèle, édite le nœud **« Préparer le contexte »** — la constante `OLLAMA_MODEL` est en haut du code, c'est le seul endroit à modifier.

## Ce que fait le workflow

```
Portail ──► Webhook ──► Récupère toutes les sources cochées
                            │  documents + régies publicitaires
                            ▼
                     Normalise et résume les données
                            │
                            ▼
                     Ollama rédige le plan du rapport (JSON)
                            │
                            ▼
                     POST du plan vers le backend
                            │
                            ▼
              Le backend génère le PowerPoint et l'archive
                            │
                            ▼
                 Le portail affiche « À relire »
```

Le **backend** produit le fichier PowerPoint, pas n8n : n8n n'a pas de nœud PPTX, et le backend est déjà en Python avec `python-pptx`. n8n se concentre sur ce qu'il fait bien — orchestrer et appeler l'IA.

**Aucun mail n'est envoyé.** Le rapport se relit puis se valide dans le portail, et se télécharge de là.

## Points d'adaptation

**Format des fichiers sources** — le backend normalise CSV, Excel, PDF, PowerPoint, texte, Markdown et JSON avant leur arrivée dans n8n. Le workflow n'est donc plus bloqué sur Excel.

**Régies publicitaires** — Meta/Instagram, Google Ads, TikTok Ads, LinkedIn Ads et Snap Ads sont récupérés par les URL temporaires de `advertising_sources`. Les jetons restent chiffrés dans le backend : n8n ne reçoit jamais les credentials.

**Qualité du rapport** — tout se joue dans le prompt du nœud « Analyse IA (Ollama) ». Le modèle reçoit un résumé des colonnes, statistiques, textes extraits et KPI publicitaires plutôt que les exports bruts. Le renderer applique ensuite le gabarit ADIGI360 de référence.

**Robustesse** — si le modèle s'écarte du format JSON attendu, le nœud « Valider le plan » retombe sur un rapport minimal plutôt que d'échouer. De même côté backend : chaque champ manquant a une valeur de repli. Un rapport imparfait vaut mieux qu'une exécution en erreur.

## Mises en page disponibles

Le plan JSON produit par l'IA accepte cinq `layout`, tous rendus aux couleurs adgi360 :

| `layout` | Rendu | Champs utilisés |
|---|---|---|
| `kpis` | Cartes de chiffres clés | `kpis` (label, value, delta), `bullets` |
| `bullets` | Deux colonnes, puces + visuel | `bullets`, `subtitle` |
| `trend` | Courbe éditable + interprétation | `categories`, `series`, `bullets` |
| `table` | Tableau détaillé éditable | `items` |
| `recommendations` | Liste numérotée | `items` (title, detail) |

Une valeur inconnue retombe sur `bullets`. Le deck ajoute automatiquement une couverture sombre et une page de fin — inutile de les demander au modèle.

## Contrat d'appel

Le backend envoie sur le webhook :

```json
{
  "review_id": "uuid",
  "client": { "id": "uuid", "name": "Acme", "contact_email": "..." },
  "additional_info": "texte libre",
  "source_files": [
    { "id": "uuid", "filename": "export.xlsx", "period": "2026-09", "retrieval_url": "http://..." }
  ],
  "advertising_sources": [
    { "platform": "google_ads", "retrieval_url": "http://..." }
  ],
  "render_callback_url": "http://host.docker.internal:8001/api/v1/auto-review/<review_id>/render"
}
```

L'URL de rappel est fournie dans le payload : rien n'est codé en dur dans le workflow.

## Avant tout déploiement

L'accès anonyme au bucket MinIO peut maintenant être retiré en production (`mc anonymous set none local/adgi360-files`) : n8n passe par les URL internes signées du backend et n'a besoin d'aucun credential S3.
