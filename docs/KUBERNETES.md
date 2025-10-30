# Kubernetes Deployment Guide

## Overview
This guide outlines a reference Kubernetes deployment for UDB components. Adapt resources & security to your cluster standards.

## Components
- `udb-api` Deployment + Service + Ingress
- Airbyte: server, worker, webapp, db (Postgres)
- Postgres (if external not provided)
- Redis
- Kafka (Strimzi or Bitnami chart)
- Optional: Dagster, Superset/Metabase
- Persistent Volumes: DuckDB data, Artifacts

## Namespace & Labels
Use a dedicated namespace: `udb`.
Recommended labels: `app.kubernetes.io/name`, `app.kubernetes.io/component`, `app.kubernetes.io/version`.

## Environment Variables (udb-api)
| Variable | Description | Default |
|----------|-------------|---------|
| `AIRBYTE_URL` | Airbyte server base URL | `http://airbyte-server:8001` |
| `DUCKDB_PATH` | Path to DuckDB file | `/data/warehouse.duckdb` |
| `ARTIFACTS_ROOT` | Artifacts root directory | `/artifacts` |
| `REDIS_URL` | Redis connection URL | optional |
| `KAFKA_BROKERS` | Kafka bootstrap servers | optional |
| `UDB_MAX_ANALYSIS_JOBS` | Parallel analysis limit | `2` |
| `UDB_ALLOWED_EGRESS_DOMAINS` | Comma-separated domains | `*` (dev) |

## Example Deployment (udb-api)
See snippet in Architecture document; additional security context below.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: udb-api
  labels:
    app: udb-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: udb-api
  template:
    metadata:
      labels:
        app: udb-api
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: udb-api
        image: ghcr.io/yourorg/udb-api:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        env:
        - name: AIRBYTE_URL
          value: http://airbyte-server:8001
        - name: DUCKDB_PATH
          value: /data/warehouse.duckdb
        volumeMounts:
        - name: data
          mountPath: /data
        - name: artifacts
          mountPath: /artifacts
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 20
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: duckdb-pvc
      - name: artifacts
        persistentVolumeClaim:
          claimName: artifacts-pvc
```

## Persistent Volumes
- DuckDB PVC: fast SSD recommended; size baseline 10Gi (expandable).
- Artifacts PVC: depends on retention; start at 20Gi; enable cleanup job.

## Network Policies
Example deny-all baseline:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```
Allow Airbyte + DNS egress:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: udb-api-egress
spec:
  podSelector:
    matchLabels:
      app: udb-api
  policyTypes: [Egress]
  egress:
  - to:
    - namespaceSelector: { matchLabels: { name: udb } }
    ports:
    - port: 8001
      protocol: TCP
  - to:
    - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } }
    ports:
    - port: 53
      protocol: UDP
```

## Ingress
Provide TLS termination; optional auth at edge for HTTP endpoints.

## Helm Chart (Planned)
A unified chart will template:
- Deployments, Services, Ingress
- ConfigMaps / Secrets
- PVCs & NetworkPolicies
- ServiceMonitor (Prometheus)

## Monitoring
- Add `ServiceMonitor` for udb-api metrics endpoint.
- Loki/EFK stack for logs (structured JSON).

## Upgrades
- Use rolling updates; verify schema compatibility.
- For DuckDB structural changes, run migration job pre-deploy.

---
Iterate this guide as Helm chart matures and more components become optional modules.
