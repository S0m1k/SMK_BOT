#!/bin/bash
set -e
TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
ARCHIVE="$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz"
# Dump Postgres
docker exec smk_bot-postgres-1 pg_dump -U smk smk > /tmp/pg_dump_smk.sql
# Archive: dump + session file
tar -czf "$ARCHIVE" \
    -C /tmp pg_dump_smk.sql \
    -C "$(pwd)/data" session.session 2>/dev/null || true
echo "Backup saved: $ARCHIVE"
