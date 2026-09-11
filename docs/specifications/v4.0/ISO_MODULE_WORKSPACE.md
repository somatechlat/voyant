# Voyant Workspace Module — ISO 29148 Specification

| Field             | Value                                      |
|-------------------|--------------------------------------------|
| **Document ID**   | VOY-SPEC-WORKSPACE-v4.0                    |
| **Module**        | `apps.workspaces` + `apps.notifications` + `apps.approvals` + `apps.core.consumers` |
| **Version**       | 4.0.0                                      |
| **Status**        | Draft                                      |
| **Classification**| Internal                                   |
| **Authors**       | Voyant Platform Engineering                |
| **Last Updated**  | 2026-01-15                                 |

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Actors and Roles](#2-actors-and-roles)
3. [Screen Mockups](#3-screen-mockups)
4. [Functional Requirements](#4-functional-requirements)
5. [Data Models](#5-data-models)
6. [API Endpoints](#6-api-endpoints)
7. [WebSocket Protocol](#7-websocket-protocol)
8. [Notification System](#8-notification-system)
9. [Approval Workflows](#9-approval-workflows)
10. [Integration Points](#10-integration-points)
11. [Non-Functional Requirements](#11-non-functional-requirements)
12. [Traceability Matrix](#12-traceability-matrix)

---

## 1. Module Overview

The **Workspace** module provides collaborative spaces for teams working within the Voyant platform. It combines three cooperating subsystems:

1. **Workspaces** — shared environments where team members collaborate on dashboards, datasets, pipelines, models, and queries.
2. **Notifications** — in-app notification center with multi-channel dispatch (in-app, email, Slack).
3. **Approval Workflows** — gated approval for sensitive operations (action executions, model deployments, policy changes, data exports).

Real-time collaboration is powered by a **WebSocket event system** that delivers live updates for ontology changes, job status updates, agent events, and scraper events.

### 1.1 Scope

| In Scope                                          | Out of Scope                        |
|---------------------------------------------------|-------------------------------------|
| Workspace CRUD + membership management            | File storage / document management  |
| Asset sharing (dashboards, datasets, pipelines, etc.) | Real-time collaborative editing |
| Threaded comments with @mentions                  | Video/voice conferencing            |
| Activity feed aggregation                         | External messaging (email sending)  |
| In-app notification center                        | Push notifications (mobile)         |
| Notification preference management               | Third-party webhook delivery        |
| Approval request lifecycle                        | Custom workflow engine              |
| Approval rule configuration                       | Fine-grained action orchestration   |
| WebSocket real-time subscriptions                 | Server-sent events (SSE)            |
| Event publishing (ontology, jobs, agents, scraper)| Cross-region replication            |

### 1.2 References

| Reference                         | Description                           |
|-----------------------------------|---------------------------------------|
| ISO 29148:2018                    | Requirements engineering standard     |
| `apps/workspaces/models.py`       | Workspace ORM models                  |
| `apps/workspaces/api.py`          | Workspace REST API                    |
| `apps/notifications/models.py`    | Notification ORM models               |
| `apps/notifications/api.py`       | Notification REST API                 |
| `apps/approvals/models.py`        | Approval ORM models                   |
| `apps/approvals/api.py`           | Approval REST API                     |
| `apps/core/consumers.py`          | WebSocket consumer                    |
| `apps/core/events.py`             | Channel-layer event publishers        |
| `apps/core/routing.py`            | WebSocket URL routing                 |

---

## 2. Actors and Roles

### 2.1 Actor Definitions

| Actor ID         | Description                                          | Source                |
|------------------|------------------------------------------------------|-----------------------|
| `workspace_owner`| Created the workspace; full admin over workspace     | Auto-assigned on creation |
| `workspace_admin`| Manages members and workspace settings               | Assigned by owner     |
| `workspace_member`| Shares assets, creates comments                     | Added by admin/owner  |
| `workspace_viewer`| Read-only access to workspace content                | Added by admin/owner  |
| `approver`       | Reviews and approves/rejects approval requests       | `write:approvals` permission |
| `requester`      | Creates approval requests                            | Authenticated user    |
| `notification_recipient` | Receives notifications                     | Authenticated user    |
| `system`         | Automated service (event triggers, workflows)        | Internal              |

### 2.2 Workspace Role Hierarchy

```
owner (4) > admin (3) > member (2) > viewer (1)
```

### 2.3 Role-Permission Matrix — Workspaces

| Permission                  | owner | admin | member | viewer |
|-----------------------------|:-----:|:-----:|:------:|:------:|
| View workspace              |   ✓   |   ✓   |   ✓    |   ✓    |
| Update workspace settings   |   ✓   |   ✓   |   ✗    |   ✗    |
| Delete workspace            |   ✓   |   ✗   |   ✗    |   ✗    |
| Add/remove members          |   ✓   |   ✓   |   ✗    |   ✗    |
| Share assets                |   ✓   |   ✓   |   ✓    |   ✗    |
| Remove assets               |   ✓   |   ✓   |   ✓    |   ✗    |
| Create comments             |   ✓   |   ✓   |   ✓    |   ✓    |
| Edit own comments           |   ✓   |   ✓   |   ✓    |   ✓    |
| Delete any comment          |   ✓   |   ✓   |   ✗    |   ✗    |
| View activity feed          |   ✓   |   ✓   |   ✓    |   ✓    |

### 2.4 Role-Permission Matrix — Approvals

| Permission                  | voyant-admin | requester | approver |
|-----------------------------|:------------:|:---------:|:--------:|
| List pending approvals      |      ✓       |    ✓*     |    ✓     |
| Create approval request     |      ✓       |    ✓      |    ✗     |
| Approve request             |      ✓       |    ✗      |    ✓     |
| Reject request              |      ✓       |    ✗      |    ✓     |
| View approval history       |      ✓       |    ✓*     |    ✓     |
| Manage approval rules       |      ✓       |    ✗      |    ✗     |

*\* Non-admin users only see their own requests.*

---

## 3. Screen Mockups

### 3.1 Workspace List

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  Workspaces                                               │
│                                                                      │
│  [+ New Workspace]                                                   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  📊 Analytics Team              owner: alice    5 members  3 assets││
│  │     "Q1 2026 analytics workspace"                                ││
│  │     Tags: [analytics] [quarterly]                                ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │  🧪 ML Experiments            owner: bob      3 members  7 assets││
│  │     "Shared ML model experiments"                                ││
│  │     Tags: [ml] [experiments]                                     ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │  🌐 Public Data Hub           owner: carol    12 members  15 assets│
│  │     "Open datasets for the whole org"         [PUBLIC]           ││
│  │     Tags: [public] [shared]                                      ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Workspace Detail

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← Back    Analytics Team                   [Edit] [Delete]         │
│  Q1 2026 analytics workspace                                        │
│                                                                      │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐           │
│  │  Assets  │ Members  │ Comments │ Activity │ Settings │           │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘           │
│                                                                      │
│  ── Shared Assets ─────────────────────────────────────────          │
│  [+ Share Asset]                                                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Type       │ ID               │ Shared By │ When                 ││
│  ├────────────┼──────────────────┼───────────┼──────────────────────││
│  │ [dashboard]│ Q1-revenue-dash  │ alice     │ 2026-01-10 14:30     ││
│  │ [dataset]  │ customer_orders  │ bob       │ 2026-01-09 09:15     ││
│  │ [pipeline] │ etl-daily-sync   │ alice     │ 2026-01-08 16:45     ││
│  └────────────┴──────────────────┴───────────┴──────────────────────┘│
│                                                                      │
│  ── Members (5) ────────────────────────────────────────             │
│  [+ Add Member]                                                      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ User         │ Role      │ Joined                               ││
│  ├──────────────┼───────────┼──────────────────────────────────────││
│  │ alice        │ [owner]   │ 2026-01-01                           ││
│  │ bob          │ [admin]   │ 2026-01-02                           ││
│  │ carol        │ [member]  │ 2026-01-03                           ││
│  │ dave         │ [member]  │ 2026-01-05                           ││
│  │ eve          │ [viewer]  │ 2026-01-07                           ││
│  └──────────────┴───────────┴──────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Notification Center

```
┌──────────────────────────────────────────────────────────────────────┐
│  🔔 Notifications                          [Mark All Read] [Filter ▼]│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ ● Job completed: Q1 revenue analysis          2 min ago          ││
│  │   Your job 'Q1 revenue analysis' has completed successfully.     ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │ ● Approval required: Model deployment          15 min ago        ││
│  │   Model v2.3 requires approval for production deployment.        ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │ ○ Data quality alert: customer_orders          1 hour ago        ││
│  │   Quality check found 3.2% null values in email column.          ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │ ○ New comment by bob on Q1-revenue-dash        3 hours ago       ││
│  │   "Can we add a regional breakdown?"                             ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ── Preferences ─────────────────────────────────────────────        │
│  Event Type            │ In-App │ Email │ Slack │                    │
│  ──────────────────────┼────────┼───────┼───────│                    │
│  job.completed         │  ✓     │  ✓    │  ✗    │                    │
│  job.failed            │  ✓     │  ✓    │  ✓    │                    │
│  approval.requested    │  ✓     │  ✗    │  ✗    │                    │
│  comment.mentioned     │  ✓     │  ✗    │  ✗    │                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4 Approval Queue

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Sidebar]  Approvals                                                │
│                                                                      │
│  ┌──────────┬──────────┐                                             │
│  │ Pending  │ History  │                                             │
│  └──────────┴──────────┘                                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Type            │ Resource            │ Requester │ When   │ Action││
│  ├─────────────────┼─────────────────────┼───────────┼────────┼───────││
│  │ [model_deploy]  │ Model: churn-v2.3   │ bob       │ 1h ago │[✓] [✗]││
│  │ [action_exec]   │ Action: send_report │ carol     │ 3h ago │[✓] [✗]││
│  │ [data_export]   │ Table: orders       │ dave      │ 5h ago │[✓] [✗]││
│  └─────────────────┴─────────────────────┴───────────┴────────┴───────┘│
│                                                                      │
│  ┌─ Approve Dialog ──────────────────────────────────────────────┐   │
│  │  Approve: Model churn-v2.3 deployment to production?          │   │
│  │  Requester: bob                                               │   │
│  │  Reason: "Accuracy validated at 94.2%, exceeds 90% threshold" │   │
│  │                                                               │   │
│  │  Your note: [____________________________________]            │   │
│  │                                                               │   │
│  │              [Cancel]  [Reject]  [Approve]                    │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 Workspaces

| FR-ID          | Requirement                                                        | Priority | Status  |
|----------------|--------------------------------------------------------------------|----------|---------|
| WS-F-001       | The system SHALL allow authenticated users to create workspaces.   | P0 | Implemented |
| WS-F-001.1     | The creator SHALL automatically be assigned the `owner` role.      | P0 | Implemented |
| WS-F-001.2     | Workspaces SHALL have a name, description, is_public flag, and tags. | P0 | Implemented |
| WS-F-002       | The system SHALL list workspaces accessible to the current user (member of + public). | P0 | Implemented |
| WS-F-003       | Workspace owners/admins SHALL be able to add members with roles: owner, admin, member, viewer. | P0 | Implemented |
| WS-F-003.1     | The system SHALL prevent duplicate memberships (unique constraint on workspace + user_id). | P0 | Implemented |
| WS-F-003.2     | The system SHALL prevent removal of the workspace owner.           | P0 | Implemented |
| WS-F-004       | Members with `member` role or higher SHALL be able to share assets (dashboard, dataset, pipeline, model, query) into the workspace. | P0 | Implemented |
| WS-F-004.1     | Assets SHALL be unique per (workspace, asset_type, asset_id).      | P0 | Implemented |
| WS-F-005       | Any workspace member (including viewers) SHALL be able to create comments. | P0 | Implemented |
| WS-F-005.1     | Comments SHALL support threading via `parent_comment_id`.          | P0 | Implemented |
| WS-F-005.2     | Comments SHALL support @mentions stored as a JSON list of user IDs. | P1 | Implemented |
| WS-F-005.3     | Only the comment author SHALL be able to edit their own comments.  | P0 | Implemented |
| WS-F-005.4     | Admins/owners SHALL be able to delete any comment; members can only delete their own. | P0 | Implemented |
| WS-F-006       | The system SHALL provide a unified activity feed aggregating member joins, asset shares, and comments. | P1 | Implemented |

### 4.2 Notifications

| FR-ID          | Requirement                                                        | Priority | Status  |
|----------------|--------------------------------------------------------------------|----------|---------|
| NTIF-F-001     | The system SHALL create in-app notifications for system events (job completed, job failed). | P0 | Implemented |
| NTIF-F-001.1   | Notifications SHALL have a type (information, warning, error, success), title, message, and optional resource reference. | P0 | Implemented |
| NTIF-F-002     | Users SHALL be able to list their notifications with filtering by type and read status. | P0 | Implemented |
| NTIF-F-002.1   | The notification list SHALL include total count and unread count.  | P0 | Implemented |
| NTIF-F-003     | Users SHALL be able to mark individual or all notifications as read. | P0 | Implemented |
| NTIF-F-004     | Users SHALL be able to delete their notifications.                 | P0 | Implemented |
| NTIF-F-005     | Users SHALL be able to manage per-event notification preferences across channels (in_app, email, slack). | P1 | Implemented |

### 4.3 Approval Workflows

| FR-ID          | Requirement                                                        | Priority | Status  |
|----------------|--------------------------------------------------------------------|----------|---------|
| APR-F-001      | The system SHALL support approval requests for: action_execution, model_deployment, policy_change, data_export. | P0 | Implemented |
| APR-F-001.1    | Approval requests SHALL track: requester, approver, status, reason, expiration, and metadata. | P0 | Implemented |
| APR-F-001.2    | Approval statuses SHALL include: pending, approved, rejected, expired. | P0 | Implemented |
| APR-F-002      | Users with `write:approvals` permission SHALL be able to approve or reject pending requests. | P0 | Implemented |
| APR-F-003      | Non-admin users SHALL only see their own pending requests.         | P0 | Implemented |
| APR-F-004      | The system SHALL provide approval rules that define auto-approve conditions and escalation timeouts. | P1 | Implemented |
| APR-F-004.1    | Approval rules SHALL be scoped by request_type and tenant.         | P0 | Implemented |
| APR-F-005      | The system SHALL provide an approval history (audit trail) of all resolved requests. | P0 | Implemented |

### 4.4 WebSocket Real-Time Events

| FR-ID          | Requirement                                                        | Priority | Status  |
|----------------|--------------------------------------------------------------------|----------|---------|
| WS-F-010       | The system SHALL provide WebSocket endpoints for real-time event subscriptions. | P0 | Implemented |
| WS-F-010.1     | WebSocket authentication SHALL be via JWT token (query param or message-level). | P0 | Implemented |
| WS-F-010.2     | Clients SHALL be able to subscribe to channels: `ontology_changes`, `job_status`, `agent_events`, `scraper_events`. | P0 | Implemented |
| WS-F-010.3     | Subscriptions SHALL be tenant-scoped; events SHALL only reach subscribers of the same tenant. | P0 | Implemented |
| WS-F-010.4     | The system SHALL support ping/pong keepalive.                      | P1 | Implemented |
| WS-F-010.5     | Events for terminal job states (completed/failed) SHALL trigger in-app notification creation. | P1 | Implemented |

---

## 5. Data Models

### 5.1 Workspace

**Table:** `voyant_workspace`

| Field          | Type         | Constraints        | Description                          |
|----------------|--------------|--------------------|--------------------------------------|
| `id`           | UUID         | PK                 | Primary key                          |
| `tenant_id`    | VARCHAR(255) | NOT NULL           | Owning tenant                        |
| `name`         | VARCHAR(255) | NOT NULL           | Workspace name                       |
| `description`  | TEXT         | default `""`       | Description                          |
| `owner_id`     | VARCHAR(256) | NOT NULL, indexed  | Owner user ID                        |
| `is_public`    | BOOLEAN      | default `false`    | Visible to all tenant users          |
| `tags`         | JSON         | default `[]`       | Categorization tags                  |
| `created_at`   | DATETIME     | auto_now_add       | Creation timestamp                   |
| `updated_at`   | DATETIME     | auto_now           | Last update timestamp                |

**Indexes:**
- `(tenant_id, owner_id)` — `idx_ws_tenant_owner`
- `(tenant_id, is_public)` — `idx_ws_tenant_public`

### 5.2 WorkspaceMember

**Table:** `voyant_workspace_member`

| Field          | Type         | Constraints                   | Description           |
|----------------|--------------|-------------------------------|-----------------------|
| `id`           | UUID         | PK                            | Primary key           |
| `tenant_id`    | VARCHAR(255) | NOT NULL                      | Owning tenant         |
| `workspace`    | FK → Workspace | CASCADE, related `members`  | Workspace             |
| `user_id`      | VARCHAR(256) | NOT NULL, indexed             | User identifier       |
| `role`         | VARCHAR(20)  | indexed                       | `owner`/`admin`/`member`/`viewer` |
| `joined_at`    | DATETIME     | default `now()`               | Join timestamp        |

**Constraints:**
- UNIQUE `(workspace, user_id)`

### 5.3 WorkspaceAsset

**Table:** `voyant_workspace_asset`

| Field          | Type         | Constraints                   | Description             |
|----------------|--------------|-------------------------------|-------------------------|
| `id`           | UUID         | PK                            | Primary key             |
| `tenant_id`    | VARCHAR(255) | NOT NULL                      | Owning tenant           |
| `workspace`    | FK → Workspace | CASCADE, related `assets`   | Workspace               |
| `asset_type`   | VARCHAR(30)  | indexed                       | `dashboard`/`dataset`/`pipeline`/`model`/`query` |
| `asset_id`     | VARCHAR(256) | NOT NULL, indexed             | Asset identifier        |
| `shared_by`    | VARCHAR(256) | NOT NULL                      | Sharing user            |
| `shared_at`    | DATETIME     | default `now()`               | Share timestamp         |

**Constraints:**
- UNIQUE `(workspace, asset_type, asset_id)`

### 5.4 Comment

**Table:** `voyant_comment`

| Field            | Type             | Constraints                   | Description               |
|------------------|------------------|-------------------------------|---------------------------|
| `id`             | UUID             | PK                            | Primary key               |
| `tenant_id`      | VARCHAR(255)     | NOT NULL                      | Owning tenant             |
| `workspace`      | FK → Workspace   | SET_NULL, nullable            | Workspace context         |
| `asset_type`     | VARCHAR(30)      | default `""`, indexed         | Asset type (blank = workspace-level) |
| `asset_id`       | VARCHAR(256)     | default `""`, indexed         | Asset identifier          |
| `content`        | TEXT             | NOT NULL                      | Comment text              |
| `parent_comment` | FK → self        | CASCADE, nullable             | Parent for threading      |
| `mentions`       | JSON             | default `[]`                  | Mentioned user IDs        |
| `created_by`     | VARCHAR(256)     | NOT NULL, indexed             | Creator user ID           |

### 5.5 Notification

**Table:** `voyant_notification`

| Field           | Type         | Constraints        | Description                          |
|-----------------|--------------|--------------------|--------------------------------------|
| `id`            | UUID         | PK                 | Primary key                          |
| `tenant_id`     | VARCHAR(255) | NOT NULL           | Owning tenant                        |
| `user_id`       | VARCHAR(256) | NOT NULL, indexed  | Recipient user                       |
| `type`          | VARCHAR(20)  | indexed            | `information`/`warning`/`error`/`success` |
| `title`         | VARCHAR(255) | NOT NULL           | Short title                          |
| `message`       | TEXT         | NOT NULL           | Full body                            |
| `resource_type` | VARCHAR(64)  | default `""`, indexed | Related resource type             |
| `resource_id`   | VARCHAR(256) | default `""`, indexed | Related resource ID               |
| `is_read`       | BOOLEAN      | default `false`, indexed | Read status                     |
| `read_at`       | DATETIME     | nullable           | Read timestamp                       |

**Indexes:**
- `(tenant_id, user_id, is_read)` — `idx_notif_tenant_user_read`
- `(tenant_id, user_id, -created_at)` — `idx_notif_tenant_user_time`

### 5.6 NotificationPreference

**Table:** `voyant_notification_preference`

| Field        | Type         | Constraints                   | Description            |
|--------------|--------------|-------------------------------|------------------------|
| `id`         | UUID         | PK                            | Primary key            |
| `tenant_id`  | VARCHAR(255) | NOT NULL                      | Owning tenant          |
| `user_id`    | VARCHAR(256) | NOT NULL, indexed             | User identifier        |
| `event_type` | VARCHAR(128) | NOT NULL, indexed             | Event type             |
| `channel`    | VARCHAR(20)  | NOT NULL                      | `in_app`/`email`/`slack` |
| `enabled`    | BOOLEAN      | default `true`                | Enabled status         |

**Constraints:**
- UNIQUE `(tenant_id, user_id, event_type, channel)`

### 5.7 ApprovalRequest

**Table:** `approval_request`

| Field           | Type         | Constraints        | Description                                |
|-----------------|--------------|--------------------|--------------------------------------------|
| `id`            | UUID         | PK                 | Primary key                                |
| `tenant_id`     | VARCHAR(255) | NOT NULL           | Owning tenant                              |
| `request_type`  | VARCHAR(32)  | indexed            | `action_execution`/`model_deployment`/`policy_change`/`data_export` |
| `resource_type` | VARCHAR(64)  | NOT NULL, indexed  | Resource type (e.g. `ActionType`)          |
| `resource_id`   | VARCHAR(256) | NOT NULL, indexed  | Resource identifier                        |
| `requester_id`  | VARCHAR(256) | NOT NULL, indexed  | Requesting user                            |
| `approver_id`   | VARCHAR(256) | default `""`, indexed | Approving user                         |
| `status`        | VARCHAR(20)  | indexed            | `pending`/`approved`/`rejected`/`expired`  |
| `reason`        | TEXT         | default `""`       | Reason / context                           |
| `approved_at`   | DATETIME     | nullable           | Resolution timestamp                       |
| `expires_at`    | DATETIME     | nullable, indexed  | Expiration timestamp                       |
| `metadata`      | JSON         | default `{}`       | Arbitrary context payload                  |

**Indexes:**
- `(tenant_id, status, -created_at)` — `idx_appr_tenant_status_created`
- `(tenant_id, request_type)` — `idx_appr_tenant_type`
- `(resource_type, resource_id)` — `idx_appr_resource`

### 5.8 ApprovalRule

**Table:** `approval_rule`

| Field                      | Type         | Constraints        | Description                   |
|----------------------------|--------------|--------------------|-------------------------------|
| `id`                       | UUID         | PK                 | Primary key                   |
| `tenant_id`                | VARCHAR(255) | NOT NULL           | Owning tenant                 |
| `name`                     | VARCHAR(255) | NOT NULL           | Rule name                     |
| `request_type`             | VARCHAR(32)  | indexed            | Request type this rule applies to |
| `auto_approve_conditions`  | JSON         | default `{}`       | Auto-approval conditions      |
| `required_approvers_count` | INTEGER      | default `1`        | Number of approvers needed    |
| `escalation_timeout_hours` | INTEGER      | default `24`       | Hours before escalation       |
| `enabled`                  | BOOLEAN      | default `true`, indexed | Rule enabled?            |

---

## 6. API Endpoints

### 6.1 Workspace Endpoints

| Method   | Path                                          | FR-ID      | Description                       | Auth / Role          |
|----------|-----------------------------------------------|------------|-----------------------------------|----------------------|
| `POST`   | `/v1/workspaces`                              | WS-F-001   | Create workspace                  | `read:*`             |
| `GET`    | `/v1/workspaces`                              | WS-F-002   | List accessible workspaces        | `read:*`             |
| `GET`    | `/v1/workspaces/{id}`                         | WS-F-002   | Get workspace details             | `read:*`             |
| `PUT`    | `/v1/workspaces/{id}`                         | WS-F-001   | Update workspace                  | `admin`+ role        |
| `DELETE` | `/v1/workspaces/{id}`                         | WS-F-001   | Delete workspace                  | `owner` role only    |
| `POST`   | `/v1/workspaces/{id}/members`                 | WS-F-003   | Add member                        | `admin`+ role        |
| `GET`    | `/v1/workspaces/{id}/members`                 | WS-F-003   | List members                      | Any member           |
| `DELETE` | `/v1/workspaces/{id}/members/{user_id}`       | WS-F-003   | Remove member                     | `admin`+ role        |
| `POST`   | `/v1/workspaces/{id}/assets`                  | WS-F-004   | Share asset                       | `member`+ role       |
| `GET`    | `/v1/workspaces/{id}/assets`                  | WS-F-004   | List shared assets                 | Any member           |
| `DELETE` | `/v1/workspaces/{id}/assets/{asset_id}`       | WS-F-004   | Remove shared asset                | `member`+ role       |
| `POST`   | `/v1/workspaces/{id}/comments`                | WS-F-005   | Create comment                     | `viewer`+ role       |
| `GET`    | `/v1/workspaces/{id}/comments`                | WS-F-005   | List comments                      | `viewer`+ role       |
| `PUT`    | `/v1/workspaces/{id}/comments/{comment_id}`   | WS-F-005   | Edit comment                       | Author only          |
| `DELETE` | `/v1/workspaces/{id}/comments/{comment_id}`   | WS-F-005   | Delete comment                     | Author or `admin`+   |
| `GET`    | `/v1/workspaces/{id}/activity`                | WS-F-006   | Activity feed                      | Any member           |

### 6.2 Notification Endpoints

| Method   | Path                                    | FR-ID       | Description                       | Auth          |
|----------|-----------------------------------------|-------------|-----------------------------------|---------------|
| `GET`    | `/v1/notifications`                     | NTIF-F-002  | List user's notifications         | `read:*`      |
| `POST`   | `/v1/notifications`                     | NTIF-F-001  | Create notification (system)      | `read:*`      |
| `PUT`    | `/v1/notifications/{id}/read`           | NTIF-F-003  | Mark single as read               | `read:*`      |
| `PUT`    | `/v1/notifications/read-all`            | NTIF-F-003  | Mark all as read                  | `read:*`      |
| `DELETE` | `/v1/notifications/{id}`                | NTIF-F-004  | Delete notification               | `read:*`      |
| `GET`    | `/v1/notifications/preferences`         | NTIF-F-005  | List preferences                  | `read:*`      |
| `PUT`    | `/v1/notifications/preferences`         | NTIF-F-005  | Update preferences (batch)        | `read:*`      |

### 6.3 Approval Endpoints

| Method   | Path                                    | FR-ID       | Description                       | Auth               |
|----------|-----------------------------------------|-------------|-----------------------------------|--------------------|
| `GET`    | `/v1/approvals/approvals`               | APR-F-001   | List pending approvals            | `read:*`           |
| `POST`   | `/v1/approvals/approvals`               | APR-F-001   | Create approval request           | `write:approvals`  |
| `PUT`    | `/v1/approvals/approvals/{id}/approve`  | APR-F-002   | Approve request                   | `write:approvals`  |
| `PUT`    | `/v1/approvals/approvals/{id}/reject`   | APR-F-002   | Reject request                    | `write:approvals`  |
| `GET`    | `/v1/approvals/approvals/history`       | APR-F-005   | Approval history                  | `read:*`           |
| `GET`    | `/v1/approvals/approvals/rules`         | APR-F-004   | List approval rules               | `read:*`           |
| `POST`   | `/v1/approvals/approvals/rules`         | APR-F-004   | Create approval rule              | `write:approvals`  |

---

## 7. WebSocket Protocol

### 7.1 Endpoints

| URL Pattern      | Consumer          | Description                  |
|------------------|-------------------|------------------------------|
| `ws://host/ws/ontology/` | `VoyantConsumer` | Ontology change notifications |
| `ws://host/ws/jobs/`     | `VoyantConsumer` | Job status updates           |
| `ws://host/ws/agents/`   | `VoyantConsumer` | Agent events                 |
| `ws://host/ws/scraper/`  | `VoyantConsumer` | Scraper events               |

All endpoints use the same `VoyantConsumer` class. Channel routing is handled via subscribe/unsubscribe actions.

### 7.2 Authentication

**Method 1: Query Parameter**
```
ws://host/ws/jobs/?token=<jwt>
```
The consumer validates the JWT immediately on `connect()`. If invalid, the connection is closed with code `4001`.

**Method 2: Message-Level Auth**
```json
{"action": "auth", "token": "<jwt>"}
```
Sent as the first message after connection. Required if no query-param token was provided.

### 7.3 Client → Server Messages

| Action         | Payload                                      | Description                    |
|----------------|----------------------------------------------|--------------------------------|
| `auth`         | `{"action": "auth", "token": "<jwt>"}`       | Authenticate the connection    |
| `subscribe`    | `{"action": "subscribe", "channels": [...]}`  | Subscribe to event channels    |
| `unsubscribe`  | `{"action": "unsubscribe", "channels": [...]}`| Unsubscribe from channels      |
| `ping`         | `{"action": "ping"}`                          | Keepalive ping                 |

### 7.4 Server → Client Messages

| Type                       | Payload                                                                     | Description                |
|----------------------------|-----------------------------------------------------------------------------|----------------------------|
| `connected`                | `{"type": "connected", "user_id": "...", "tenant_id": "..."}`              | Post-connect (query-param auth) |
| `auth_required`            | `{"type": "auth_required", "message": "..."}`                              | Auth required              |
| `authenticated`            | `{"type": "authenticated", "user_id": "...", "tenant_id": "..."}`          | Post message-level auth    |
| `auth_failed`              | `{"type": "auth_failed", "message": "..."}`                                | Auth failure               |
| `subscription.confirmed`   | `{"type": "subscription.confirmed", "channels": [...]}`                    | Channels confirmed         |
| `unsubscription.confirmed` | `{"type": "unsubscription.confirmed", "channels": [...]}`                  | Channels updated           |
| `event`                    | `{"type": "event", "channel": "<ch>", "data": {...}}`                      | Real-time event            |
| `pong`                     | `{"type": "pong"}`                                                         | Keepalive response         |
| `error`                    | `{"type": "error", "message": "..."}`                                      | Error message              |

### 7.5 Valid Channels

| Channel              | Event Type                  | Data Fields                                    |
|----------------------|-----------------------------|------------------------------------------------|
| `ontology_changes`   | `event_ontology_change`     | `event_type`, `object_type`, `object_id`       |
| `job_status`         | `event_job_status`          | `job_id`, `status`, `progress`                 |
| `agent_events`       | `event_agent_event`         | `agent_id`, `event_type`                       |
| `scraper_events`     | `event_scraper_event`       | `event_type`, `template_id`, `template_name`   |

### 7.6 Group Naming Convention

```
voyant_{tenant_id}_{channel}
```

Example: `voyant_tenant-abc_job_status`

### 7.7 Event Publishing

Events are published to channel-layer groups by helper functions in `apps/core/events.py`:

| Function                     | Channel             | Called When                    |
|------------------------------|---------------------|--------------------------------|
| `publish_ontology_change()`  | `ontology_changes`  | Ontology CRUD operations       |
| `publish_job_status()`       | `job_status`        | Job status transitions         |
| `publish_agent_event()`      | `agent_events`      | Agent platform events          |
| `publish_scraper_event()`    | `scraper_events`    | Scraper lifecycle events       |

`publish_job_status()` also creates in-app notifications via `NotificationService` for terminal states (completed/failed) when a `user_id` is provided.

### 7.8 WebSocket Connection Flow

```
Client                    Server (VoyantConsumer)
  │                              │
  │──── WS Connect ─────────────>│
  │                              │
  │  (if ?token= provided)       │
  │<─── {"type":"connected"} ────│  (auth via query param)
  │                              │
  │  (if no token)               │
  │<─── {"type":"auth_required"} │  (must send auth message)
  │                              │
  │── {"action":"auth",          │
  │    "token":"<jwt>"} ────────>│
  │<── {"type":"authenticated"} ─│
  │                              │
  │── {"action":"subscribe",     │
  │    "channels":["job_status"]}│
  │<── {"type":                  │
  │    "subscription.confirmed"} │
  │                              │
  │       ... (events flow) ...  │
  │                              │
  │<── {"type":"event",          │
  │    "channel":"job_status",   │
  │    "data":{...}} ───────────│
  │                              │
  │── {"action":"ping"} ────────>│
  │<── {"type":"pong"} ──────────│
  │                              │
  │──── WS Disconnect ──────────>│
  │                              │  (leaves all groups)
```

---

## 8. Notification System

### 8.1 Notification Lifecycle

```
Event Triggered
       │
       ▼
┌──────────────┐     ┌─────────────────────┐
│ publish_job_ │────>│ NotificationService  │
│ status()     │     │   .create()          │
└──────────────┘     └──────────┬──────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌──────────┐ ┌─────────┐ ┌─────────┐
              │ In-App   │ │ Email   │ │ Slack   │
              │ (stored) │ │ (TBD)   │ │ (TBD)   │
              └──────────┘ └─────────┘ └─────────┘
                    │
                    ▼
              ┌──────────────┐
              │ User sees    │
              │ notification │
              │ in center    │
              └──────────────┘
```

### 8.2 Notification Types

| Type        | Color    | Use Case                              |
|-------------|----------|---------------------------------------|
| `information` | Blue   | General information                   |
| `warning`     | Amber  | Data quality alerts, approaching limits |
| `error`       | Red    | Job failures, system errors           |
| `success`     | Green  | Job completions, approvals            |

### 8.3 Preference Channels

| Channel  | Status       | Description                    |
|----------|--------------|--------------------------------|
| `in_app` | Implemented  | In-app notification center     |
| `email`  | Schema only  | Email delivery (future)        |
| `slack`  | Schema only  | Slack webhook delivery (future)|

---

## 9. Approval Workflows

### 9.1 Approval Request Lifecycle

```
                  ┌───────────┐
                  │  Created  │
                  └─────┬─────┘
                        │
                        ▼
                  ┌───────────┐
            ┌─────│  Pending  │─────┐
            │     └───────────┘     │
            │                       │
            ▼                       ▼
     ┌─────────────┐       ┌──────────────┐
     │  Approved   │       │  Rejected    │
     └─────────────┘       └──────────────┘
                                  
     (also)  ┌───────────┐
             │  Expired  │  ← auto-expired by escalation_timeout_hours
             └───────────┘
```

### 9.2 Request Types

| Request Type       | Description                           | Typical Metadata                     |
|--------------------|---------------------------------------|--------------------------------------|
| `action_execution` | Gating for sensitive action runs      | action params, risk score            |
| `model_deployment` | Deploying ML model to production      | model version, accuracy metrics      |
| `policy_change`    | Modifying governance policies         | policy diff, impact assessment       |
| `data_export`      | Exporting data outside the platform   | table names, row counts, destination |

### 9.3 Auto-Approve Conditions

Approval rules can define `auto_approve_conditions` as JSON:

```json
{
  "max_risk_score": 3,
  "allowed_stages": ["staging"],
  "tags": ["low-risk"]
}
```

When a request matches all conditions, it can be auto-approved without human intervention.

---

## 10. Integration Points

| System         | Integration Type    | Direction | Description                                      |
|----------------|---------------------|-----------|--------------------------------------------------|
| **Keycloak**   | JWT authentication  | Inbound   | WebSocket + API auth                             |
| **Django Channels** | Channel layer  | Internal  | Redis-backed pub/sub for WebSocket events        |
| **Redis**      | Channel layer backend| Internal | Message broker for channel-layer groups          |
| **Kafka**      | Event streaming     | Parallel  | Channel-layer events run alongside Kafka emitters |
| **Temporal**   | Workflow orchestration| Outbound | Approval auto-expiration workflows               |
| **PostgreSQL** | Django ORM          | Internal  | All workspace/notification/approval persistence  |
| **Notification Service** | Internal service | Internal | Creates notifications from events            |

---

## 11. Non-Functional Requirements

| NFR-ID      | Requirement                                                           | Target     |
|-------------|-----------------------------------------------------------------------|------------|
| WS-NF-001   | WebSocket connection auth SHALL complete within 2 seconds.            | 2s p99     |
| WS-NF-002   | Event delivery latency from publish to client receipt SHALL be <500ms.| 500ms p95  |
| WS-NF-003   | The system SHALL support 10,000 concurrent WebSocket connections.     | 10,000     |
| WS-NF-004   | Notification queries SHALL return within 200ms for <1000 notifications.| 200ms p95 |
| WS-NF-005   | Workspace operations SHALL enforce tenant isolation.                  | 100%       |
| WS-NF-006   | Approval workflows SHALL complete lifecycle tracking within 100ms.   | 100ms p99  |
| WS-NF-007   | The channel layer SHALL use Redis as the backing store.               | Required   |

---

## 12. Traceability Matrix

| Requirement  | Data Model                | API Endpoint                              | UI Component            |
|--------------|---------------------------|-------------------------------------------|-------------------------|
| WS-F-001     | `Workspace`               | `/v1/workspaces` (POST)                   | Workspace list          |
| WS-F-002     | `Workspace`, `WorkspaceMember` | `/v1/workspaces` (GET)                | Workspace list          |
| WS-F-003     | `WorkspaceMember`         | `/v1/workspaces/{id}/members`             | Member management       |
| WS-F-004     | `WorkspaceAsset`          | `/v1/workspaces/{id}/assets`              | Asset sharing           |
| WS-F-005     | `Comment`                 | `/v1/workspaces/{id}/comments`            | Comment thread          |
| WS-F-006     | Aggregated                | `/v1/workspaces/{id}/activity`            | Activity feed           |
| NTIF-F-001   | `Notification`            | `/v1/notifications` (POST)                | Notification center     |
| NTIF-F-002   | `Notification`            | `/v1/notifications` (GET)                 | Notification center     |
| NTIF-F-003   | `Notification`            | `/v1/notifications/read-all` (PUT)        | Notification center     |
| NTIF-F-005   | `NotificationPreference`  | `/v1/notifications/preferences`           | Preference settings     |
| APR-F-001    | `ApprovalRequest`         | `/v1/approvals/approvals` (POST)          | Approval queue          |
| APR-F-002    | `ApprovalRequest`         | `/v1/approvals/approvals/{id}/approve`    | Approval queue          |
| APR-F-004    | `ApprovalRule`            | `/v1/approvals/approvals/rules`           | Rule management         |
| APR-F-005    | `ApprovalRequest`         | `/v1/approvals/approvals/history`         | Approval history        |
| WS-F-010     | — (consumer)              | WebSocket `ws://host/ws/{channel}/`       | Real-time updates       |
