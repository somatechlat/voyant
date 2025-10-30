# Event Schema

## Overview
Events are emitted over Kafka (if configured) and represent job lifecycle transitions and completion summaries.
All events share a common envelope:
```
{
  "type": "job.created|job.state.changed|job.analyze.completed",
  "jobId": "<id>",
  "jobType": "sync|analyze|ingest",
  "state": "running|succeeded|failed|timeout|...",
  "timestamp": "ISO8601",
  "extra": { ... }  // type-specific enrichment
}
```

## job.created
Emitted when a job is first registered.
Extra fields (may vary by jobType):
- sync: connectionId, sourceId
- analyze: tenant
- ingest: table, fragments, tenant

## job.state.changed
Emitted when sync job reaches terminal or timeout state.
Extra:
- none currently (future: duration, error reason)

## job.analyze.completed
Emitted after successful `/analyze` execution.
Extra fields:
- kpiRows: integer (count of KPI rowsets)
- tenant: tenant identifier (if provided)
- durationSec: float duration round( seconds, 3 )
- qualityStatus: success|error|skipped
- driftStatus: success|error|skipped

## Future Additions
- errorReason for failed jobs
- artifactCounts (profile, quality, drift, charts)
- tableName(s) involved

## Compatibility
Unrecognized fields should be ignored by consumers. Envelope keys are stable; extra is additive.
