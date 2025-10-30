# MCP Interface Specification

UDB exposes a set of MCP tools enabling agent-driven data connectivity & analysis.

## Transport
- JSON-RPC 2.0 over stdio or WebSocket (depending on host environment).
- Each tool invocation includes a correlation ID; responses include same ID.

## Tools
### `udb.discover_connect`
Detect source type, provision Airbyte source/destination/connection, trigger initial sync.
Input schema:
```json
{
  "type": "object",
  "properties": {
    "hint": {"type":"string"},
    "credentials": {"type":"object"},
    "destination": {"type":"string", "enum":["duckdb","postgres"], "default":"duckdb"},
    "options": {"type":"object"}
  },
  "required":["hint"]
}
```
Response example:
```json
{ "sourceId":"src_abc", "destinationId":"dst_def", "connectionId":"cnx_ghi", "jobId":12345, "oauthUrl":null }
```
If OAuth required prior to sync, `oauthUrl` is non-null and `jobId` may be deferred until after authorization.

### `udb.analyze`
Run normalization (light), profiling, quality, KPI SQL, chart generation.
Input schema:
```json
{
  "type":"object",
  "properties":{
    "connectionIds": {"type":"array","items":{"type":"string"}},
    "uploads": {"type":"array","items":{"type":"string"}},
    "joins": {"type":"array","items":{"type":"string"}},
    "kpiSql": {"type":"string"},
    "profile": {"type":"boolean","default": true},
    "quality": {"type":"boolean","default": true},
    "chartsSpec": {"type":"object"}
  }
}
```
Response example:
```json
{
  "jobId": "b7e93d",
  "summary": "Pulled 1 connection + 1 upload; joined on customer_id; computed 3 KPIs.",
  "kpis": [{"region":"LATAM","revenue":123456,"avg_margin":0.31}],
  "artifacts": {
    "profileHtml": "/artifact/b7e93d/profile.html",
    "profileJson": "/artifact/b7e93d/profile.json",
    "qualityHtml": "/artifact/b7e93d/quality.html",
    "qualityJson": "/artifact/b7e93d/quality.json",
    "charts": ["/artifact/b7e93d/charts/revenue_by_region.html"]
  }
}
```

### `udb.status`
Return status for a job (discover, sync, analyze).
Response:
```json
{ "state":"queued|running|succeeded|failed", "progress":42, "logsUrl":"/logs/job/123" }
```

### `udb.artifact`
Return signed or relative URL to artifact path.
Input:
```json
{ "jobId":"b7e93d", "path":"profile.html" }
```
Response:
```json
{ "url":"/artifact/b7e93d/profile.html" }
```

### `udb.sql`
Guarded ad-hoc SQL (SELECT only + limited CREATE VIEW) for quick derived queries.
Input:
```json
{ "sql":"select * from some_view limit 20" }
```
Response:
```json
{ "columns":["col1","col2"], "rows":[[1,"a"],[2,"b"]], "rowCount":2 }
```

## Error Handling
Errors follow JSON-RPC `error` object spec; `data` field includes `error_code`, `jobId` (if available), and optional remediation hint.

## Versioning
- `mcpInterfaceVersion` exposed via `udb.capabilities` (future tool) for backward compatibility negotiation.

## Rate Limiting & Quotas
Future addition: soft quotas per tenant — number of active sync jobs, artifact size caps.

---
This interface may evolve; maintain backward compatibility for existing fields where possible.
