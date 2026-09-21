# Publier Digital 360

Ce document répond à une seule question : **comment mettre la plateforme en
ligne**, avec quel hébergeur, à quel prix, et dans quel ordre.

---

## 1. Ce qu'il faut héberger

La plateforme n'est pas une simple page web. Elle comporte six briques, et
c'est ce qui écarte d'emblée les hébergeurs « front seulement » (Vercel,
Netlify, GitHub Pages) :

| Brique | Rôle | Contrainte |
|---|---|---|
| Frontend React | l'interface | fichiers statiques, trivial à héberger |
| API FastAPI | toute la logique | processus permanent |
| PostgreSQL | comptes, clients, factures | **données persistantes** |
| MinIO / S3 | fichiers sources, PPTX, PDF | **données persistantes** |
| n8n | orchestration de l'analyse | processus permanent + webhooks publics |
| IA | rédige le contenu des rapports | soit beaucoup de RAM, soit une API |

Deux briques stockent des données qui ne doivent jamais disparaître. C'est
le vrai critère de choix : un hébergeur sans volumes persistants et sans
sauvegardes est disqualifié, quel que soit son prix.

---

## 2. Choix de l'hébergeur

### Recommandation : un VPS chez OVHcloud, à Beauharnois (Québec)

**VPS-3 — 6 vCore, 12 Go de RAM, 100 Go NVMe — environ 17 $ CA / mois.**

Trois raisons, dans cet ordre d'importance :

1. **Les données restent au Québec.** Vous vendez à des agences québécoises
   qui vous confient les données de performance de *leurs* clients. La Loi 25
   impose d'évaluer tout transfert hors Québec, et un acheteur d'ici posera
   la question dès le premier appel commercial. « Nos serveurs sont à
   Beauharnois » ferme le sujet ; « nos serveurs sont en Virginie » ouvre un
   dossier de conformité. C'est un argument de vente, pas une contrainte.
2. **12 Go de RAM suffisent à faire tourner l'IA localement**, donc à garder
   le coût marginal d'un rapport à zéro.
3. **Prix fixe.** Pas de facture qui triple parce qu'un workflow a bouclé.

### Ce que ça coûte, au total

| Poste | Coût mensuel |
|---|---|
| VPS OVH VPS-3 (Beauharnois) | ~17 $ CA |
| Nom de domaine `.ca` | ~2 $ CA |
| Certificats TLS (Let's Encrypt via Caddy) | 0 $ |
| n8n auto-hébergé (édition communautaire) | 0 $ |
| **Total** | **~19 $ CA / mois** |

À comparer aux mêmes briques en services gérés : n8n Cloud Starter seul
coûte 20 €/mois, Render facture 25 $/mois d'abonnement **plus** 19 $ pour le
plus petit Postgres géré **plus** 7 $ par service — on dépasse 80 $ US avant
d'avoir hébergé quoi que ce soit.

### Les alternatives, et pourquoi elles ne gagnent pas ici

- **Railway** (5 $/mois d'abonnement Hobby puis à l'usage, ~0,014 $/Go-RAM/h)
  — le plus agréable à utiliser : `git push` et c'est en ligne, Postgres et
  volumes inclus. Le bon choix **si vous ne voulez pas administrer un
  serveur**. Deux réserves : la facture suit la consommation, et les régions
  disponibles ne comprennent pas le Québec.
- **Render** (Hobby gratuit, Pro 25 $/mois) — sérieux, sites statiques
  gratuits, mais la note monte vite dès qu'on additionne API + Postgres +
  disque, et l'IA locale n'y a pas sa place.
- **Fly.io** — excellent pour du multi-région, complexité inutile pour un
  produit qui démarre.
- **Hetzner** (~16 €/mois pour 4 vCPU / 8 Go) — le meilleur rapport
  performance/prix du marché, mais aucun centre de données au Canada. À
  reconsidérer le jour où vous vendez surtout en Europe.
- **AWS / GCP / Azure** — région `ca-central-1` disponible, mais la
  complexité et le coût ne se justifient qu'à partir de plusieurs dizaines
  d'agences clientes.

> **Le jour où ça grossit**, le chemin de migration est déjà tracé :
> Postgres géré (OVH ou Neon), fichiers sur Cloudflare R2
> (0,015 $/Go-mois, **sortie gratuite** — c'est ce qui compte quand on sert
> des PowerPoint), et plusieurs conteneurs backend derrière le même proxy.
> Aucune de ces bascules ne demande de réécrire du code : ce sont des
> variables d'environnement.

---

## 3. La question de l'IA

C'est le seul point où le déploiement diffère vraiment du poste de
développement. Sur votre Mac, Ollama profite de la puce Apple ; sur un VPS
sans carte graphique, le même modèle tourne **beaucoup** plus lentement.

**Option A — Ollama sur le VPS** (`--profile ollama`)
Un modèle 8B quantifié occupe ~6 Go de RAM et génère un plan de rapport en
quelques minutes sur 6 vCPU. Acceptable : la génération est de toute façon
asynchrone, l'utilisateur ne l'attend pas devant son écran. Coût marginal
nul, données jamais transmises à un tiers.

**Option B — une API** (Claude Haiku 4.5 : 1 $ / M jetons en entrée,
5 $ / M en sortie). Un rapport consomme de l'ordre de 10 000 jetons, soit
**moins de 0,05 $ par rapport** — quelques dollars par mois pour une agence
active. La qualité rédactionnelle est nettement supérieure à celle d'un
modèle 8B, et le VPS peut alors être deux fois plus petit.

**En pratique :** commencez en A pour valider la chaîne sans facture ni
engagement, puis basculez en B quand la qualité des textes deviendra un
argument commercial. Le changement se limite à un nœud du workflow n8n —
l'appel HTTP à Ollama devient un appel HTTP à l'API. Le backend, lui, ne
change pas : il reçoit le même JSON.

---

## 4. Ce qui a été préparé

| Fichier | Rôle |
|---|---|
| `Portail-backend/Dockerfile` | image de l'API, deux étages, utilisateur non root |
| `Portail-front end/Dockerfile` | compile le React puis le sert avec Caddy |
| `deploy/docker-compose.prod.yml` | les six services, réseau interne |
| `deploy/Caddyfile` | reverse proxy, HTTPS automatique, en-têtes de sécurité |
| `deploy/.env.prod.example` | tous les secrets à remplir |
| `deploy/sauvegarde.sh` | dump quotidien base + fichiers, rétention 30 jours |

Deux choix structurants, à connaître :

**Seul Caddy est exposé.** Postgres, MinIO, le backend et n8n n'ont aucun
port publié : ils ne sont joignables que depuis le réseau Docker interne. Un
scan de ports du serveur ne trouve que 80 et 443.

**Le bucket n'est plus public.** En développement, le bucket MinIO avait été
ouvert en anonyme pour que n8n puisse lire les fichiers — c'était un
raccourci, et il aurait exposé les données de tous les clients en ligne. Le
backend transmet désormais à n8n une **URL pré-signée valable 30 minutes**
par fichier. Le bucket reste privé, et cette correction vaut aussi pour votre
poste : relancez `mc anonymous set none local/adgi360-files`.

---

## 5. Mise en ligne, étape par étape

### a. Préparer le domaine

Acheter le domaine, puis créer trois enregistrements **A** vers l'IP du VPS :

```
app.digital360.ca     A    <IP du serveur>
files.digital360.ca   A    <IP du serveur>
n8n.digital360.ca     A    <IP du serveur>
```

Faire ceci **avant** le premier démarrage : Caddy demande les certificats au
lancement, et la validation échoue si le DNS ne pointe pas encore.

### b. Préparer le serveur

```bash
ssh root@<IP>
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh

# Pare-feu : rien d'autre que SSH et le web.
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
```

### c. Déposer le code et les secrets

```bash
git clone git@github.com:<votre-compte>/digital360-backend.git
git clone git@github.com:<votre-compte>/digital360-frontend.git

cp deploy/.env.prod.example deploy/.env.prod
# Générer une valeur différente pour CHAQUE secret :
openssl rand -hex 32
nano deploy/.env.prod
```

### d. Démarrer

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod \
  up -d --build

# Avec l'IA locale :
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod \
  --profile ollama up -d --build
docker compose -f deploy/docker-compose.prod.yml exec ollama ollama pull llama3.1
```

### e. Vérifier

```bash
curl https://app.digital360.ca/api/v1/health     # doit répondre 200
curl -I https://files.digital360.ca/digital360-files/  # doit répondre 403
```

Le **403 sur le stockage est le résultat attendu** : il prouve que le bucket
est bien privé. Un 200 signifierait que l'accès anonyme est encore actif.

Puis, dans le navigateur : créer le premier compte sur
`https://app.digital360.ca`, importer le workflow dans n8n
(`https://n8n.digital360.ca`), et lancer une review de bout en bout.

### f. Sauvegardes

```bash
chmod +x deploy/sauvegarde.sh
crontab -e
# 15 3 * * * /root/digital360/deploy/sauvegarde.sh
```

Puis **restaurer une sauvegarde sur une autre machine, une fois**. Une
sauvegarde jamais restaurée n'est pas une sauvegarde.

---

## 6. À faire avant d'ouvrir à un premier client payant

Ces points ne bloquent pas une mise en ligne de démonstration, mais ils
bloquent une vente :

1. **Migrations Alembic.** Aujourd'hui les tables sont créées au démarrage
   (`create_all`). Cela fonctionne tant que le schéma ne change pas ; à la
   première évolution en production, il faudra des migrations versionnées.
2. **Sauvegardes hors du serveur.** Le script actuel écrit sur le disque du
   VPS : il protège d'une erreur humaine, pas de la perte du serveur.
   Copier les archives vers un stockage objet distinct.
3. **Réinitialisation de mot de passe.** Sans envoi d'e-mail, c'est vous qui
   réinitialisez en base. Tenable à trois utilisateurs, pas à trente.
4. **Supervision.** Un simple contrôle externe de `/api/v1/health` toutes les
   cinq minutes suffit pour commencer.
5. **Journalisation des accès.** Qui s'est connecté, quand — attendu dès
   qu'un client demande un questionnaire de sécurité.

---

## Annexe — Commander le VPS, pas à pas

### a. Avant de commander : créer la clé SSH

À faire **avant** la commande : OVH propose d'installer la clé au moment de la
livraison, ce qui évite d'avoir à se connecter par mot de passe ne serait-ce
qu'une fois. Sur le Mac :

```bash
ssh-keygen -t ed25519 -C "digital360"
# Entrée pour accepter ~/.ssh/id_ed25519
# Une phrase de passe : recommandée, elle protège la clé si le Mac est volé

pbcopy < ~/.ssh/id_ed25519.pub   # la clé PUBLIQUE est maintenant dans le presse-papiers
```

Ne jamais partager le fichier **sans** `.pub` : c'est la clé privée, elle ne
quitte jamais la machine.

### b. Créer le compte

Sur **ca.ovh.com** (le site canadien — c'est lui qui facture en dollars
canadiens et qui donne accès aux centres de données du Québec). Créer un
compte **entreprise** au nom d'adigi360, avec le numéro d'entreprise :
la facture sert de pièce comptable et la TPS/TVQ devient récupérable.

### c. Commander le VPS

Menu **Bare Metal Cloud → VPS**, puis :

| Champ | Valeur | Pourquoi |
|---|---|---|
| Gamme | **VPS-3** (6 vCore, 12 Go, 100 Go NVMe) | 12 Go permettent de faire tourner l'IA localement |
| Centre de données | **Canada — Beauharnois (BHS)** | le point qui justifie tout le choix : les données restent au Québec |
| Système | **Ubuntu 24.04 LTS** | version à support long, celle que suppose le guide |
| Panneau (Plesk / cPanel) | **aucun** | inutile : tout passe par Docker |
| Clé SSH | coller la clé publique de l'étape a | |
| Engagement | **mensuel** | garder la liberté de changer d'avis les premiers mois |
| Sauvegarde automatique | **incluse**, la garder | |
| IP supplémentaire, Load Balancer, Windows | **non** | |

**Vérifier l'emplacement avant de payer.** C'est le seul réglage qu'on ne peut
pas modifier après coup : changer de région impose de recréer le serveur.

Compter environ **17 $ CA/mois**, soit ~19,35 $ avec TPS et TVQ. Aucuns frais
d'installation. La livraison prend de quelques minutes à une heure.

### d. Première connexion

OVH envoie un courriel avec l'adresse IP et l'identifiant (`ubuntu` ou `root`
selon l'image).

```bash
ssh ubuntu@<IP>          # ou root@<IP>
sudo apt update && sudo apt upgrade -y
```

Si la connexion est refusée, c'est presque toujours que la livraison n'est pas
terminée — l'espace client affiche l'état du serveur.

### e. Sécuriser (dix minutes, à ne pas sauter)

Un serveur exposé sur Internet reçoit des tentatives de connexion
automatisées dans l'heure qui suit sa mise en ligne. Trois réglages suffisent
à les rendre inoffensives :

```bash
# 1. Un utilisateur non root pour le travail quotidien
sudo adduser louis
sudo usermod -aG sudo louis
sudo rsync --archive --chown=louis:louis ~/.ssh /home/louis

# 2. Interdire le mot de passe et la connexion root directe
sudo nano /etc/ssh/sshd_config
#   PasswordAuthentication no
#   PermitRootLogin no
sudo systemctl restart ssh

# 3. Pare-feu : SSH et le web, rien d'autre
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable
```

**Avant de fermer la session, ouvrir un second terminal et vérifier que
`ssh louis@<IP>` fonctionne.** Une erreur dans `sshd_config` verrouille le
serveur ; tant que la première session reste ouverte, on peut corriger.

Puis Docker :

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker louis   # se déconnecter/reconnecter pour l'appliquer
```

### f. Le nom de domaine

Se prendre chez **OVH** (tout sur une seule facture) ou chez **Cloudflare
Registrar** (vendu au prix coûtant, sans marge, et le DNS y est plus rapide).
Un `.ca` coûte de 15 à 25 $ CA par an.

Créer ensuite trois enregistrements **A** vers l'IP du serveur :

```
app     A    <IP>
files   A    <IP>
n8n     A    <IP>
```

Vérifier la propagation avant de démarrer la pile — Caddy demande les
certificats dès le lancement et Let's Encrypt limite les tentatives :

```bash
dig +short app.digital360.ca    # doit renvoyer l'IP du serveur
```

À partir de là, reprendre la **section 5** de ce document.
