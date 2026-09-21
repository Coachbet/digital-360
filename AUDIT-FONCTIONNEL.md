# Parcours de test et limites — 21 septembre 2026

## Livré dans ce lot

- Création de client depuis Données et Auto Review : nom, activité, courriel facultatif, erreurs serveur affichées.
- Données : recherche par nom, confirmation de suppression, période via sélecteur de mois, retour après import, protection contre les réponses désordonnées lors du changement de client.
- Auto Review : import Excel par glisser-déposer ou sélection multiple, sélection/désélection globale, ajout de client sans quitter le formulaire.
- Formats réellement pris en charge explicités ; les connecteurs publicitaires ne sont plus présentés comme sources utilisables par le workflow actuel.
- Serveur : contrôle que les fichiers appartiennent au client sélectionné, vérification du format Excel, correction du changement de statut après rappel n8n.
- Routes d’aperçu PDF et suppression des rapports, avec contrôle d’agence et refus de suppression pendant la génération.
- LibreOffice ajouté à l’image backend pour les nouveaux aperçus. Les anciens rapports sans PDF restent téléchargeables en PowerPoint.
- Mon agence : erreur visible et bouton Réessayer au lieu d’un écran blanc.
- Actualisation manuelle des rapports et message si l’analyse se prolonge.

## Test manuel après redéploiement

1. Données → Ajouter un client → nommer un client de démonstration, choisir son activité et créer.
2. Vérifier qu’il est sélectionné, choisir septembre 2026 et glisser le dataset Excel.
3. Rechercher le fichier par son nom puis effacer la recherche.
4. Auto Review → sélectionner ce client → cocher le fichier → Générer.
5. Vérifier l’exécution n8n puis attendre le statut À relire ; ouvrir l’aperçu et télécharger le PPTX.
6. Valider le rapport. Tester sa suppression sur un rapport de démonstration uniquement.
7. Créer un second client : ses fichiers doivent être distincts de ceux du premier.
8. Tester un fichier non Excel dans Auto Review : un message doit expliquer le refus.

## Limites restantes / prochain lot

- Workflow IA : Excel .xlsx, première feuille, échantillon de 30 lignes. Pas d’analyse exhaustive du classeur ni de CSV/PDF/PPT comme sources.
- Les erreurs d’exécution internes à n8n ne remontent pas encore automatiquement au statut du rapport ; une analyse peut rester en cours. Vérifier les exécutions n8n.
- Connexions publicitaires, facturation et calendrier : pas de validation de bout en bout sur le VPS dans ce lot.
- Gestion complète des clients (modification, archivage, suppression avec conservation de l’historique) à définir et implémenter.
- Les imports multiples n’ont pas encore de barre de progression par fichier ni de reprise après interruption.

La compilation frontend et les tests backend locaux ne remplacent pas le parcours réel avec PostgreSQL, MinIO, n8n et Ollama. Aucun déploiement distant n’a été effectué dans ce lot.
