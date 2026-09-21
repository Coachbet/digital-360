# Image de production du frontend Digital 360.
#
# Le résultat est un Caddy qui sert les fichiers statiques compilés et joue en
# même temps le rôle de reverse proxy TLS pour tout le reste de la plateforme.
# Caddy obtient et renouvelle les certificats Let's Encrypt tout seul : il n'y a
# ni certbot ni cron à maintenir.

FROM node:20-alpine AS builder

WORKDIR /build
# Les dépendances sont copiées seules d'abord : tant que package-lock.json ne
# change pas, Docker réutilise le cache et la construction reste rapide.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM caddy:2-alpine

COPY --from=builder /build/dist /srv
# Le Caddyfile est monté depuis deploy/ au lieu d'être copié : changer de nom de
# domaine ne demande alors pas de reconstruire l'image.
