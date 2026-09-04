# Voyant v3.0.0 — Disaster Recovery Runbook

## Overview

This runbook covers every failure mode for the Voyant standalone cluster.
Every procedure is designed to be executed by a single operator with shell access.

---

## Quick Reference

| Scenario | Command |
|----------|---------|
| Full bootstrap from zero | `./scripts/ops/voyant.sh bootstrap` |
| Backup everything | `./scripts/ops/voyant.sh backup` |
| Restore from backup | `./scripts/ops/voyant.sh restore <timestamp>` |
| Rotate secrets | `./scripts/ops/voyant.sh secrets rotate` |
| System diagnostics | `./scripts/ops/voyant.sh doctor` |
| Check status | `./scripts/ops/voyant.sh status` |

---

## Scenario 1: Complete Cluster Loss (from zero)

**Trigger:** Machine wiped, Docker volumes lost, no containers exist.

**Recovery:**
```bash
# 1. Clone repo
git clone https://github.com/somatech/voyant.git && cd voyant

# 2. Restore secrets from secure backup (if available)
#    Option A: Copy backed-up secrets/ directory to infra/standalone/secrets/
#    Option B: Let bootstrap generate new ones (breaks existing Keycloak/MinIO)
cp -r /secure/backup/secrets infra/standalone/secrets

# 3. Full bootstrap (idempotent)
./scripts/ops/voyant.sh bootstrap

# 4. Restore data from backup (if available)
./scripts/ops/voyant.sh restore <timestamp>

# 5. Verify
./scripts/ops/voyant.sh doctor
./scripts/ops/voyant.sh test
```

**RTO:** ~15 minutes (bootstrap) + restore time (~5 min for typical dataset)
**RPO:** Last backup timestamp (default: every 6 hours)

---

## Scenario 2: Postgres Data Loss

**Trigger:** Postgres volume corrupted, accidental DROP DATABASE, disk failure.

**Recovery:**
```bash
# 1. Stop application services
docker compose -f infra/standalone/docker-compose.yml stop voyant_api voyant_worker

# 2. Restore from backup
./scripts/ops/voyant.sh restore <timestamp>

# 3. Verify
docker exec voyant_postgres psql -U voyant -c "SELECT count(*) FROM voyant_job;"
./scripts/ops/voyant.sh test
```

**If no backup exists:**
```bash
# Reinitialize empty database
docker exec voyant_postgres psql -U postgres -c "DROP DATABASE IF EXISTS voyant;"
docker exec voyant_postgres psql -U postgres -c "CREATE DATABASE voyant OWNER voyant;"
docker exec voyant_api python manage.py migrate --noinput
# All job history, artifacts metadata, governance data LOST.
```

---

## Scenario 3: Vault Data Loss

**Trigger:** Vault volume wiped, Vault dev-mode restart (dev mode loses data on restart).

**Recovery:**
```bash
# 1. Vault is in dev mode — secrets are in /run/secrets/ files
#    Re-seed from secret files
./scripts/ops/voyant.sh bootstrap  # Step 5 re-seeds Vault

# 2. If secret files are also lost, restore from backup
./scripts/ops/voyant.sh restore <timestamp>
```

**Production note:** Switch Vault to production mode with Raft storage backend
for persistent, HA storage. Dev mode is NOT durable.

---

## Scenario 4: Redis Data Loss

**Trigger:** Redis volume wiped, crash without persistence.

**Impact:** Session cache, rate limiting counters, temporary data lost.
**Not critical** — Redis is a cache layer, not primary storage.

**Recovery:**
```bash
# Redis auto-recovers empty. Restart if needed:
docker compose -f infra/standalone/docker-compose.yml restart voyant_redis

# If you need cached data, restore from backup:
./scripts/ops/voyant.sh restore <timestamp>
```

---

## Scenario 5: MinIO Data Loss

**Trigger:** MinIO volume wiped, disk failure.

**Impact:** All analysis artifacts (charts, PDFs, CSVs) lost. Metadata in Postgres remains.

**Recovery:**
```bash
# 1. Recreate bucket
docker exec voyant_minio mc mb --ignore-existing local/voyant-artifacts

# 2. Restore artifacts from backup
./scripts/ops/voyant.sh restore <timestamp>

# 3. If no backup, artifacts are gone. Jobs will show missing artifacts.
#    Re-run analysis jobs to regenerate.
```

---

## Scenario 6: Milvus Data Loss

**Trigger:** Milvus volume wiped, etcd corruption.

**Impact:** All vector embeddings lost. Semantic search returns empty results.

**Recovery:**
```bash
# 1. Milvus auto-creates collections on first use (milvus_auto_create=True)
# 2. Re-index documents via API
curl -X POST http://localhost:45000/v1/search/index \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "metadata": {...}}'

# 3. For bulk re-indexing, use the MCP tool or write a script
```

---

## Scenario 7: Secret Compromise

**Trigger:** Secret leaked, unauthorized access detected.

**Recovery:**
```bash
# 1. IMMEDIATELY rotate all secrets
./scripts/ops/voyant.sh secrets rotate

# 2. Verify new secrets are active
./scripts/ops/voyant.sh secrets status

# 3. Invalidate any external tokens (Keycloak, etc.)
# 4. Review audit logs
docker exec voyant_postgres psql -U voyant -c \
  "SELECT * FROM voyant_audit_log WHERE created_at > now() - interval '24 hours' ORDER BY created_at DESC LIMIT 50;"

# 5. If MinIO keys were compromised, also rotate MinIO root credentials
#    (requires recreating the MinIO container with new keys)
```

---

## Scenario 8: Docker Daemon Crash

**Trigger:** Docker daemon restart, machine reboot.

**Recovery:**
```bash
# Containers with restart:always policy auto-recover.
# Verify:
./scripts/ops/voyant.sh status

# If containers didn't restart:
./scripts/ops/voyant.sh up

# Full verification:
./scripts/ops/voyant.sh doctor
```

---

## Scenario 9: API Container Crash Loop

**Trigger:** Bad code deploy, config error, dependency failure.

**Recovery:**
```bash
# 1. Check logs
docker logs voyant_api --tail 50

# 2. Common fixes:
#    - Config error: check .env and Vault secrets
#    - Migration needed: docker exec voyant_api python manage.py migrate
#    - Dependency failure: check Postgres/Redis/Temporal health

# 3. Nuclear option — rebuild from scratch
docker compose -f infra/standalone/docker-compose.yml up -d --force-recreate voyant_api

# 4. If code is broken, revert to last known good commit
git log --oneline -5
git checkout <good-commit>
docker compose -f infra/standalone/docker-compose.yml up -d --build voyant_api
```

---

## Backup Strategy

### Automated Backups (Recommended)

```bash
# Add to crontab (every 6 hours):
0 */6 * * * /path/to/scripts/ops/backup-cron.sh >> /var/log/voyant-backup.log 2>&1
```

### What Gets Backed Up

| Component | Method | Size | Criticality |
|-----------|--------|------|-------------|
| PostgreSQL | `pg_dump -Fc` | ~10-100MB | **CRITICAL** — all metadata |
| Redis | RDB snapshot | ~1-10MB | Low — cache layer |
| MinIO | `mc cp --recursive` | Variable | Medium — artifacts regenerable |
| Vault | API export | ~1KB | **CRITICAL** — all secrets |
| DuckDB | File copy | Variable | Medium — analytical cache |
| Milvus | Metadata JSON | ~1KB | Low — embeddings regenerable |
| Secrets | File copy | ~1KB | **CRITICAL** — all keys |
| Config | File copy | ~2KB | Low — in git |

### Backup Retention

- **Default:** 7 days (28 backups at 6-hour intervals)
- **Configurable:** Set `VOYANT_BACKUP_RETENTION_DAYS` env var
- **Recommended:** Keep at least 1 weekly backup for 30 days

### Offsite Backup (Recommended)

```bash
# Sync to S3/GCS after each local backup
aws s3 sync /path/to/backups/ s3://voyant-backups/ --delete
# or
gsutil -m rsync -r /path/to/backups/ gs://voyant-backups/
```

---

## Pre-Production Checklist

- [ ] Run `./scripts/ops/voyant.sh bootstrap` from clean state
- [ ] Run `./scripts/ops/voyant.sh doctor` — 0 issues
- [ ] Run `./scripts/ops/voyant.sh test` — all pass
- [ ] Run `./scripts/ops/voyant.sh backup` — verify backup integrity
- [ ] Test restore: `./scripts/ops/voyant.sh restore <ts>` on separate machine
- [ ] Set up automated backup cron
- [ ] Set up offsite backup sync
- [ ] Configure monitoring alerts (Prometheus/Grafana)
- [ ] Document runbook access for on-call team
