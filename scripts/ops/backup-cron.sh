#!/usr/bin/env bash
# =============================================================================
# VOYANT — Automated Backup Cron Job
# =============================================================================
# Add to crontab:
#   0 */6 * * * /path/to/scripts/ops/backup-cron.sh >> /var/log/voyant-backup.log 2>&1
#
# Retention: keeps last 7 days of backups (28 at 6-hour intervals).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOYANT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="${VOYANT_BACKUP_DIR:-$VOYANT_ROOT/backups}"
RETENTION_DAYS="${VOYANT_BACKUP_RETENTION_DAYS:-7}"

echo "=== Automated Backup: $(date -Iseconds) ==="

# Run backup
"$SCRIPT_DIR/voyant.sh" backup

# Prune old backups
if [[ -d "$BACKUP_DIR" ]]; then
  pruned=0
  find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +${RETENTION_DAYS} | while read -r dir; do
    rm -rf "$dir"
    ((pruned++)) || true
    echo "Pruned: $(basename "$dir")"
  done
  echo "Pruned $pruned backups older than $RETENTION_DAYS days"
fi

echo "=== Backup complete: $(date -Iseconds) ==="
