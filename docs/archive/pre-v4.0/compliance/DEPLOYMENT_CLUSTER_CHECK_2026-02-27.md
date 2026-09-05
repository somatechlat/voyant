# Deployment Cluster Check

Date: 2026-02-27  
Scope: deployment assets under `infra/` and root Docker build context

## Checks Executed

1. Docker Compose render (standalone)
- Command: `docker compose -f infra/standalone/docker-compose.yml --env-file infra/standalone/.env config`
- Result: pass
- Notes:
  - No unresolved variable warnings after updating `infra/standalone/.env.example` defaults.
  - Bind-mount path audit reports `MISSING_BIND_COUNT 0`.

2. Docker Compose render (integrated)
- Command: `docker compose -f infra/integrated/docker-compose.yml --env-file infra/integrated/.env.integrated config`
- Result: pass

3. Helm chart lint
- Command: `helm lint infra/standalone/helm/udb-api`
- Result: pass
- Command: `helm lint infra/standalone/helm/voyant-udb`
- Result: pass

4. Helm chart template render
- Command: `helm template udb-api infra/standalone/helm/udb-api`
- Result: pass
- Command: `helm template voyant-udb infra/standalone/helm/voyant-udb`
- Result: pass

5. Kubernetes manifest structural validation (offline)
- Method: parse all documents in `infra/standalone/k8s/*.yaml` and assert each doc has `apiVersion` and `kind`.
- Result: pass (`K8S_YAML_OK 11`)

## Fixes Applied During Check

1. Helm template variable declaration fixes:
- `infra/standalone/helm/udb-api/templates/ingress.yaml`
  - `range $k, $v in ...` -> `range $k, $v := ...`
- `infra/standalone/helm/udb-api/templates/deployment.yaml`
  - `range $k, $v in ...` -> `range $k, $v := ...`

2. Helm chart metadata validity:
- `infra/standalone/helm/voyant-udb/Chart.yaml`
  - Replaced empty `home` and `sources` with valid URLs.
  - Added non-empty `icon` URL.

3. Compose bind mount correction:
- `infra/standalone/docker-compose.yml`
  - `./scripts/sql/init-db.sql` -> `./scripts/init-db.sql` (correct relative path)

4. Standalone environment defaults for reproducible config:
- `infra/standalone/.env.example`
  - Added concrete defaults for required Postgres/Redis/Kafka/Temporal/DataHub/MinIO/Keycloak/Lago and health-check variables.

## Remaining External Blocker

- Full Docker image build/run validation could not be executed in this environment because Docker daemon is not running (`docker.sock` unavailable).

## Conclusion

- Deployment manifests/configuration are structurally consistent and render successfully for Compose and Helm.
- Cluster deployment assets are now in a deployable state from a configuration perspective.
