#!/bin/sh
# Sauvegarde quotidienne de Digital 360 : base de données + fichiers.
#
# À installer sur le serveur :
#   chmod +x deploy/sauvegarde.sh
#   crontab -e   →   15 3 * * * /chemin/vers/deploy/sauvegarde.sh
#
# Une sauvegarde que personne n'a jamais restaurée n'est pas une sauvegarde :
# tester la restauration au moins une fois, sur une autre machine.

set -eu

DEST="${BACKUP_DIR:-/var/backups/digital360}"
JOUR="$(date +%Y-%m-%d)"
COMPOSE="docker compose -f $(dirname "$0")/docker-compose.prod.yml --env-file $(dirname "$0")/.env.prod"

mkdir -p "$DEST"

# Base de données — dump logique, restaurable sur une autre version de Postgres.
$COMPOSE exec -T postgres pg_dump -U "${POSTGRES_USER:-digital360}" \
  "${POSTGRES_DB:-digital360}" | gzip > "$DEST/db-$JOUR.sql.gz"

# Fichiers — miroir du bucket MinIO.
$COMPOSE exec -T minio sh -c '
  mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
  mc mirror --overwrite --quiet local/'"${S3_BUCKET:-digital360-files}"' /data/.backup
' || echo "Miroir MinIO ignoré"

# Rétention : 30 jours. Au-delà, une sauvegarde n'a plus de valeur légale ni
# pratique, et remplit le disque.
find "$DEST" -name 'db-*.sql.gz' -mtime +30 -delete

echo "Sauvegarde du $JOUR terminée dans $DEST"
