#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=/opt/blog_li/.env
BACKUP_DIR=/root/backups
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE" >&2; exit 1; }
set -a
source "$ENV_FILE"
set +a

mkdir -p "$BACKUP_DIR"
MYSQL_PWD="${DB_PASSWORD:?}" mysqldump \
  --single-transaction \
  --quick \
  -h"${DB_HOST:-localhost}" \
  -P"${DB_PORT:-3306}" \
  -u"${DB_USER:?}" \
  "${DB_NAME:?}" | gzip > "$BACKUP_DIR/blog-$(date +%F).sql.gz"

find "$BACKUP_DIR" -maxdepth 1 -name 'blog-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
rsync -a --delete /opt/blog_li/media/ "$BACKUP_DIR/media/"
