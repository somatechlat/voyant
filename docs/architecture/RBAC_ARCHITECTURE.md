# VOYANT RBAC ARCHITECTURE
# Role-Based Access Control with Realm Isolation

**Document ID:** VOYANT-ARCH-RBAC-3.1.0
**Status:** APPROVED
**Date:** 2026-05-21
**Classification:** Security Architecture
**Compliance:** ISO/IEC 27001:2022, ISO/IEC 25010:2011, OWASP Top 10 2021, NIST CSF 2.0

---

## 1. EXECUTIVE SUMMARY

Voyant implements **three-layer defense-in-depth authorization**:

1. **Keycloak Realm + Role Authentication** (AuthN + coarse AuthZ)
2. **SpiceDB Fine-Grained Relationship-Based Access Control** (ReBAC)
3. **Role-Aware Data Filtering** (row-level, column-level, field-level)

**Golden Rule:** *No user can read, write, or execute any data outside their assigned role, realm, and tenant boundary. Period.*

---

## 2. SECURITY DOMAINS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REALM BOUNDARY                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           TENANT A                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │   │
│  │  │  voyant-    │  │  voyant-    │  │  voyant-    │  │ voyant-   │ │   │
│  │  │  admin      │  │  engineer   │  │  analyst    │  │ viewer    │ │   │
│  │  │             │  │             │  │             │  │           │ │   │
│  │  │  ALL data   │  │  sources,   │  │  read +     │  │ dashboards│ │   │
│  │  │  ALL realms │  │  jobs, SQL  │  │  SQL,       │  │ reports   │ │   │
│  │  │  ALL tenants│  │  presets    │  │  presets    │  │ artifacts │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │   │
│  │                                                                     │   │
│  │  DATA ISOLATION: Admin sees everything. Engineer cannot see        │   │
│  │  billing. Analyst cannot create sources. Viewer cannot see SQL.    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           TENANT B                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │   │
│  │  │  voyant-    │  │  voyant-    │  │  voyant-    │  │ voyant-   │ │   │
│  │  │  admin      │  │  engineer   │  │  analyst    │  │ viewer    │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │   │
│  │                                                                     │   │
│  │  CROSS-TENANT ISOLATION: Tenant B users CANNOT see Tenant A data   │   │
│  │  even if they have the same role.                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. ROLE DEFINITIONS

### 3.1 Keycloak Realm Roles

| Role | Hierarchy | Data Access | Operations | Scope |
|------|-----------|-------------|------------|-------|
| **voyant-admin** | Top (composite of all) | All tenants, all realms, all data | CRUD + execute + manage + delete | System-wide |
| **voyant-engineer** | Mid (composite of analyst) | Own tenant only | Read all + write sources/jobs + execute SQL/presets + scraping | Tenant-scoped |
| **voyant-analyst** | Mid (composite of viewer) | Own tenant only | Read all + execute SQL/presets | Tenant-scoped |
| **voyant-viewer** | Bottom | Own tenant only | Read dashboards, reports, artifacts only | Tenant-scoped |

### 3.2 Permission Matrix

| Permission | Admin | Engineer | Analyst | Viewer |
|------------|-------|----------|---------|--------|
| `read:sources` | ✅ | ✅ | ✅ | ❌ |
| `write:sources` | ✅ | ✅ | ❌ | ❌ |
| `delete:sources` | ✅ | ❌ | ❌ | ❌ |
| `read:jobs` | ✅ | ✅ | ✅ | ❌ |
| `write:jobs` | ✅ | ✅ | ❌ | ❌ |
| `cancel:jobs` | ✅ | ✅ | ❌ | ❌ |
| `execute:sql` | ✅ | ✅ | ✅ | ❌ |
| `execute:presets` | ✅ | ✅ | ✅ | ❌ |
| `read:artifacts` | ✅ | ✅ | ✅ | ✅ |
| `write:artifacts` | ✅ | ✅ | ❌ | ❌ |
| `read:reports` | ✅ | ✅ | ✅ | ✅ |
| `read:dashboards` | ✅ | ✅ | ✅ | ✅ |
| `read:governance` | ✅ | ✅ | ✅ | ❌ |
| `write:governance` | ✅ | ❌ | ❌ | ❌ |
| `read:quotas` | ✅ | ✅ | ❌ | ❌ |
| `write:quotas` | ✅ | ❌ | ❌ | ❌ |
| `read:audit` | ✅ | ❌ | ❌ | ❌ |
| `execute:scrape` | ✅ | ✅ | ❌ | ❌ |
| `execute:research` | ✅ | ✅ | ✅ | ❌ |
| `read:vectors` | ✅ | ✅ | ✅ | ❌ |
| `write:vectors` | ✅ | ✅ | ❌ | ❌ |
| `manage:users` | ✅ | ❌ | ❌ | ❌ |
| `manage:realms` | ✅ | ❌ | ❌ | ❌ |
| `*` (wildcard) | ✅ | ❌ | ❌ | ❌ |

---

## 4. REALM ISOLATION ARCHITECTURE

### 4.1 Keycloak Realm Boundaries

```python
# apps/core/security/auth.py — REALM ENFORCEMENT
class KeycloakAuth:
    def validate_token(self, token: str) -> User:
        payload = jwt.decode(...)
        
        # EXTRACT REALM
        issuer = payload.get("iss", "")
        realm = issuer.split("/realms/")[-1] if "/realms/" in issuer else "default"
        
        # EXTRACT ROLES (realm-scoped)
        realm_access = payload.get("realm_access", {})
        roles = realm_access.get("roles", [])
        
        # EXTRACT TENANT (custom claim)
        tenant_id = payload.get("tenant_id", "default")
        
        # VALIDATE: realm must match configured realm
        if realm != self._realm:
            raise HttpError(403, "ERR_AUTH_WRONG_REALM")
        
        return User(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            username=payload.get("preferred_username"),
            tenant_id=tenant_id,
            realm=realm,
            roles=roles,
            permissions=self._derive_permissions(roles),
            token=token,
        )
```

### 4.2 Realm Isolation Rules

| Rule | Enforcement |
|------|-------------|
| **R1** | A token from `realm-a` CANNOT access `realm-b` endpoints |
| **R2** | Admin in `realm-a` CANNOT see data from `realm-b` |
| **R3** | Each realm has independent user directories, roles, and clients |
| **R4** | Cross-realm access requires explicit `realm->realm` trust mapping in SpiceDB |
| **R5** | Service accounts are realm-scoped; no global service account |

---

## 5. TENANT ISOLATION + RBAC

### 5.1 Dual Enforcement

Every database query, vector search, and workflow dispatch performs **two checks**:

```python
def enforce_access(request, resource_type: str, action: str):
    user = get_current_user(request)
    
    # CHECK 1: Role Permission (can this role do this action?)
    required_perm = f"{action}:{resource_type}"
    if not user.has_permission(required_perm):
        raise HttpError(403, f"Role '{user.roles}' lacks permission '{required_perm}'")
    
    # CHECK 2: Tenant Isolation (can this user see this tenant's data?)
    target_tenant = get_tenant_from_request(request)
    if user.tenant_id != target_tenant and "voyant-admin" not in user.roles:
        raise HttpError(403, "ERR_AUTH_CROSS_TENANT")
    
    # CHECK 3: SpiceDB ReBAC (fine-grained, optional, for resource-level)
    if not check_spicedb_permission(user.user_id, resource_type, action):
        raise HttpError(403, "ERR_AUTH_SPICEDB_DENIED")
```

### 5.2 Tenant-Aware Models (ALL models)

```python
# apps/core/models.py — EVERY model inherits this
class TenantModel(models.Model):
    tenant_id = models.CharField(max_length=64, db_index=True)
    realm = models.CharField(max_length=64, db_index=True, default="default")
    
    class Meta:
        abstract = True
        # Composite index enforces tenant + realm scoping
        indexes = [
            models.Index(fields=["realm", "tenant_id", "created_at"]),
        ]
        # Row-level security hint for PostgreSQL RLS (future)
```

### 5.3 Query Auto-Filtering

```python
# apps/core/middleware.py — Auto-inject tenant/realm filtering
class RBACQueryMiddleware:
    """Automatically filters all ORM queries by tenant_id + realm."""
    
    def __call__(self, request):
        user = get_optional_user(request)
        if user:
            # Inject into thread-local for ORM managers
            set_current_user(user)
        return self.get_response(request)
```

```python
# apps/core/models.py — Custom Manager
class RBACManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        user = get_current_user_or_none()
        if user and "voyant-admin" not in user.roles:
            # VIEWERS, ANALYSTS, ENGINEERS only see their tenant + realm
            qs = qs.filter(
                tenant_id=user.tenant_id,
                realm=user.realm,
            )
        elif user and "voyant-admin" in user.roles:
            # Admins can optionally filter by ?tenant_id= query param
            requested_tenant = get_query_param("tenant_id")
            if requested_tenant:
                qs = qs.filter(tenant_id=requested_tenant, realm=user.realm)
            # If no tenant specified, admin sees ALL tenants in their realm
            # Cross-realm admin access requires explicit realm param
            requested_realm = get_query_param("realm")
            if requested_realm and requested_realm != user.realm:
                # Only super-admins can cross realms
                if not user.has_permission("manage:realms"):
                    raise HttpError(403, "ERR_AUTH_CROSS_REALM")
                qs = qs.filter(realm=requested_realm)
        return qs
```

---

## 6. RESOURCE-LEVEL RBAC (SpiceDB)

### 6.1 Enhanced SpiceDB Schema

```zed
// apps/core/security/schema.zed — ENHANCED

definition user {}

definition realm {
    relation admin: user
    relation member: user

    permission view = member + admin
    permission manage = admin
}

definition tenant {
    relation realm: realm
    relation admin: user
    relation engineer: user
    relation analyst: user
    relation viewer: user

    permission view = viewer + analyst + engineer + admin + realm->view
    permission create_source = engineer + admin + realm->manage
    permission execute_sql = analyst + engineer + admin + realm->manage
    permission execute_scrape = engineer + admin + realm->manage
    permission execute_research = analyst + engineer + admin + realm->manage
    permission manage = admin + realm->manage
}

definition resource {
    relation tenant: tenant
    relation owner: user
    relation viewer: user
    relation editor: user

    permission view = viewer + editor + owner + tenant->view
    permission edit = editor + owner + tenant->create_source
    permission delete = owner + tenant->manage
    permission execute = tenant->execute_sql + tenant->execute_scrape + tenant->execute_research
}

// Specific resource types
definition source {
    relation tenant: tenant
    relation owner: user

    permission view = owner + tenant->view
    permission edit = owner + tenant->create_source
    permission delete = owner + tenant->manage
    permission ingest = owner + tenant->create_source
}

definition scrape_job {
    relation tenant: tenant
    relation owner: user

    permission view = owner + tenant->view
    permission cancel = owner + tenant->manage
}

definition research_report {
    relation tenant: tenant
    relation owner: user

    permission view = owner + tenant->view
    permission delete = owner + tenant->manage
}

definition vector_document {
    relation tenant: tenant
    relation owner: user

    permission view = owner + tenant->view
    permission index = owner + tenant->create_source
    permission delete = owner + tenant->manage
}

definition artifact {
    relation tenant: tenant
    relation owner: user

    permission view = owner + tenant->view
    permission download = owner + tenant->view
    permission delete = owner + tenant->manage
}
```

### 6.2 SpiceDB Permission Checks

```python
# apps/core/lib/policy.py — SpiceDB integration
class SpiceRBAC:
    def check_permission(self, user_id: str, resource_type: str, resource_id: str, action: str) -> bool:
        """
        Check if user has permission on a specific resource.
        Example: check_permission("user-123", "source", "src-456", "view")
        """
        response = self._client.check_permission(
            consistency=Consistency(fully_consistent=True),
            resource=ObjectReference(
                object_type=resource_type,
                object_id=resource_id,
            ),
            permission=action,
            subject=SubjectReference(
                object=ObjectReference(object_type="user", object_id=user_id)
            ),
        )
        return response.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
    
    def ensure_tenant_access(self, user_id: str, tenant_id: str, action: str) -> bool:
        """Check if user has action permission on tenant."""
        return self.check_permission(user_id, "tenant", tenant_id, action)
```

---

## 7. RBAC IN NEW MODULES

### 7.1 Milvus Vector Store RBAC

```python
# apps/search/lib/milvus_store.py — RBAC-AWARE VECTOR SEARCH
class RBACMilvusStore:
    def search(self, query_embedding, user: User, top_k=10):
        # ROLE CHECK: does user have read:vectors?
        if not user.has_permission("read:vectors"):
            raise HttpError(403, "ERR_AUTH_VECTORS_READ")
        
        # TENANT FILTER: always inject tenant_id + realm
        filter_expr = f'tenant_id == "{user.tenant_id}" AND realm == "{user.realm}"'
        
        # VIEWER RESTRICTION: viewers can only search their own indexed docs
        if "voyant-viewer" in user.roles and "voyant-admin" not in user.roles:
            filter_expr += f' AND owner_id == "{user.user_id}"'
        
        return self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=top_k,
            expr=filter_expr,
            output_fields=["doc_id", "content", "metadata"],
        )
    
    def index_document(self, doc, user: User):
        # ROLE CHECK: only engineers+ can index
        if not user.has_permission("write:vectors"):
            raise HttpError(403, "ERR_AUTH_VECTORS_WRITE")
        
        # Inject ownership
        doc.metadata["owner_id"] = user.user_id
        doc.tenant_id = user.tenant_id
        doc.realm = user.realm
        
        return self.collection.insert(doc)
    
    def delete_document(self, doc_id, user: User):
        # ROLE CHECK: owner or admin or manage:vectors
        doc = self.get_by_doc_id(doc_id)
        if doc.metadata.get("owner_id") != user.user_id and not user.has_permission("delete:vectors"):
            raise HttpError(403, "ERR_AUTH_VECTORS_DELETE")
        
        return self.collection.delete(f'doc_id == "{doc_id}"')
```

### 7.2 Octopus Scraping RBAC

```python
# apps/scraper/octopus/dispatcher.py — RBAC-AWARE DISPATCH
class OctopusDispatcher:
    async def dispatch(self, request: OctopusRequest, user: User) -> OctopusResult:
        # ROLE CHECK: can user execute scraping?
        if not user.has_permission("execute:scrape"):
            raise HttpError(403, "ERR_AUTH_SCRAPE_EXECUTE")
        
        # TENANT ENFORCEMENT
        request.tenant_id = user.tenant_id
        request.realm = user.realm
        
        // VIEWER RESTRICTION: viewers cannot scrape at all
        if "voyant-viewer" in user.roles:
            raise HttpError(403, "ERR_AUTH_SCRAPE_VIEWER_BLOCKED")
        
        // ANALYST RESTRICTION: analysts can use templates only, no custom workflows
        if "voyant-analyst" in user.roles and "voyant-engineer" not in user.roles:
            if not request.template_id:
                raise HttpError(403, "ERR_AUTH_SCRAPE_ANALYST_TEMPLATE_ONLY")
        
        // QUOTA CHECK per role
        quota = self._get_role_quota(user.roles[0])
        if self._tenant_usage(user.tenant_id) >= quota:
            raise HttpError(429, "ERR_QUOTA_EXCEEDED")
        
        return await self._execute(request)
```

### 7.3 Deep Research RBAC

```python
# apps/scraper/deep_research/workflow.py — RBAC-AWARE RESEARCH
class DeepResearchWorkflowV2:
    async def run(self, query: str, breadth: int, depth: int, user: User):
        # ROLE CHECK
        if not user.has_permission("execute:research"):
            raise HttpError(403, "ERR_AUTH_RESEARCH_EXECUTE")
        
        // VIEWER BLOCKED
        if "voyant-viewer" in user.roles:
            raise HttpError(403, "ERR_AUTH_RESEARCH_VIEWER_BLOCKED")
        
        // ANALYST: breadth/depth capped
        if "voyant-analyst" in user.roles and "voyant-engineer" not in user.roles:
            breadth = min(breadth, 3)
            depth = min(depth, 2)
        
        // ENGINEER: normal limits
        // ADMIN: unlimited
        
        // Tag report with owner for RBAC filtering
        report = await self._research(query, breadth, depth)
        report.owner_id = user.user_id
        report.tenant_id = user.tenant_id
        report.realm = user.realm
        
        return report
```

### 7.4 SQL RBAC

```python
# apps/sql/api.py — RBAC-AWARE SQL
@sql_router.post("/query", auth=require_permission("execute:sql"))
def sql_query(request, payload: SQLQuery):
    user = get_current_user(request)
    
    // VIEWER BLOCKED (require_permission already blocks)
    
    // ANALYST: read-only enforced by TrinoClient
    // ENGINEER: read-only enforced
    // ADMIN: can bypass read-only if explicit ?admin=true (audited)
    
    if payload.query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "DROP", "ALTER")):
        if "voyant-admin" not in user.roles:
            raise HttpError(403, "ERR_AUTH_SQL_WRITE_BLOCKED")
        
        // Admin write queries are heavily audited
        AuditLog.objects.create(
            actor=user.user_id,
            action="sql_write",
            resource_type="sql_query",
            outcome="allowed_admin_override",
            details={"query": payload.query[:1000]},
            realm=user.realm,
            tenant_id=user.tenant_id,
        )
    
    return TrinoClient.execute(payload.query)
```

### 7.5 Governance / Quotas RBAC

```python
# apps/governance/api.py — RBAC-AWARE GOVERNANCE
@governance_router.get("/quotas", auth=require_permission("read:quotas"))
def get_quotas(request):
    user = get_current_user(request)
    
    // ENGINEER: sees own tenant quotas
    // ANALYST: blocked (no read:quotas)
    // ADMIN: sees all quotas in realm
    
    if "voyant-admin" in user.roles:
        return QuotaTier.objects.filter(realm=user.realm)
    else:
        return QuotaTier.objects.filter(tenant_id=user.tenant_id, realm=user.realm)
```

---

## 8. API ENDPOINT RBAC MATRIX

### 8.1 Core API

| Endpoint | Method | Required Permission | Admin Only |
|----------|--------|---------------------|------------|
| `/health` | GET | None | No |
| `/ready` | GET | None | No |
| `/v1/sources` | GET | `read:sources` | No |
| `/v1/sources` | POST | `write:sources` | No |
| `/v1/sources/{id}` | DELETE | `delete:sources` | No |
| `/v1/jobs` | GET | `read:jobs` | No |
| `/v1/jobs` | POST | `write:jobs` | No |
| `/v1/jobs/{id}/cancel` | POST | `cancel:jobs` | No |
| `/v1/sql/query` | POST | `execute:sql` | No |
| `/v1/artifacts` | GET | `read:artifacts` | No |
| `/v1/artifacts/{id}/download` | GET | `read:artifacts` | No |
| `/v1/governance/quotas` | GET | `read:quotas` | No |
| `/v1/governance/quotas` | PUT | `write:quotas` | Yes |
| `/v1/analyze` | POST | `execute:presets` | No |
| `/v1/search/index` | POST | `write:vectors` | No |
| `/v1/search/query` | POST | `read:vectors` | No |
| `/v1/scrape/start` | POST | `execute:scrape` | No |
| `/v1/deep_research` | POST | `execute:research` | No |
| `/v1/admin/audit` | GET | `read:audit` | Yes |
| `/v1/admin/users` | GET | `manage:users` | Yes |
| `/v1/admin/realms` | GET | `manage:realms` | Yes |

### 8.2 MCP Tool RBAC Matrix

| MCP Tool | Required Permission | Viewer | Analyst | Engineer | Admin |
|----------|---------------------|--------|---------|----------|-------|
| `voyant.discover` | `read:sources` | ❌ | ✅ | ✅ | ✅ |
| `voyant.connect` | `write:sources` | ❌ | ❌ | ✅ | ✅ |
| `voyant.ingest` | `write:jobs` | ❌ | ❌ | ✅ | ✅ |
| `voyant.profile` | `execute:presets` | ❌ | ✅ | ✅ | ✅ |
| `voyant.quality` | `execute:presets` | ❌ | ✅ | ✅ | ✅ |
| `voyant.analyze` | `execute:presets` | ❌ | ✅ | ✅ | ✅ |
| `voyant.kpi` | `execute:sql` | ❌ | ✅ | ✅ | ✅ |
| `voyant.sql` | `execute:sql` | ❌ | ✅ | ✅ | ✅ |
| `voyant.search` | `read:vectors` | ❌ | ✅ | ✅ | ✅ |
| `voyant.vector.index` | `write:vectors` | ❌ | ❌ | ✅ | ✅ |
| `scrape.fetch` | `execute:scrape` | ❌ | ❌ | ✅ | ✅ |
| `scrape.template` | `execute:scrape` | ❌ | ❌ | ✅ | ✅ |
| `deep_research` | `execute:research` | ❌ | ✅ | ✅ | ✅ |
| `voyant.lineage` | `read:governance` | ❌ | ✅ | ✅ | ✅ |
| `voyant.quotas` | `read:quotas` | ❌ | ❌ | ✅ | ✅ |
| `voyant.admin.audit` | `read:audit` | ❌ | ❌ | ❌ | ✅ |
| `voyant.admin.users` | `manage:users` | ❌ | ❌ | ❌ | ✅ |

---

## 9. DATA VISIBILITY MATRIX

### 9.1 What Each Role Can See

| Data Category | Viewer | Analyst | Engineer | Admin |
|---------------|--------|---------|----------|-------|
| **Sources** | ❌ | ✅ (read) | ✅ (CRUD) | ✅ (all realms) |
| **Jobs** | ❌ | ✅ (read) | ✅ (CRUD) | ✅ (all realms) |
| **SQL Results** | ❌ | ✅ | ✅ | ✅ |
| **Artifacts** | ✅ (own) | ✅ (tenant) | ✅ (tenant) | ✅ (all) |
| **Reports** | ✅ (own) | ✅ (tenant) | ✅ (tenant) | ✅ (all) |
| **Vectors** | ❌ | ✅ (search) | ✅ (search+index) | ✅ (all) |
| **Scrape Jobs** | ❌ | ❌ | ✅ (tenant) | ✅ (all) |
| **Research Reports** | ❌ | ✅ (own) | ✅ (tenant) | ✅ (all) |
| **Governance** | ❌ | ✅ (read) | ✅ (read) | ✅ (write) |
| **Quotas** | ❌ | ❌ | ✅ (own tenant) | ✅ (all) |
| **Audit Logs** | ❌ | ❌ | ❌ | ✅ (realm) |
| **User Management** | ❌ | ❌ | ❌ | ✅ (realm) |
| **Proxy Configs** | ❌ | ❌ | ❌ | ✅ (realm) |
| **System Settings** | ❌ | ❌ | ❌ | ✅ (realm) |

### 9.2 Cross-Tenant Visibility

| Actor | Can See Tenant A | Can See Tenant B | Can See Tenant C |
|-------|-----------------|-----------------|-----------------|
| Admin in Realm X | ✅ | ✅ | ✅ |
| Engineer in Tenant A | ✅ | ❌ | ❌ |
| Analyst in Tenant A | ✅ | ❌ | ❌ |
| Viewer in Tenant A | ✅ (limited) | ❌ | ❌ |

### 9.3 Cross-Realm Visibility

| Actor | Can See Realm X | Can See Realm Y |
|-------|----------------|----------------|
| Super Admin | ✅ | ✅ (with explicit realm param) |
| Admin in Realm X | ✅ | ❌ |
| Engineer in Realm X | ✅ | ❌ |

---

## 10. AUDIT & COMPLIANCE

### 10.1 RBAC Audit Events

Every RBAC decision is logged:

```python
class AuditEvent(Enum):
    AUTH_DENIED_ROLE = "auth.denied.role"          # Wrong role
    AUTH_DENIED_REALM = "auth.denied.realm"        # Cross-realm attempt
    AUTH_DENIED_TENANT = "auth.denied.tenant"      # Cross-tenant attempt
    AUTH_DENIED_PERMISSION = "auth.denied.permission"  # Missing permission
    AUTH_DENIED_RESOURCE = "auth.denied.resource"  # SpiceDB denied
    AUTH_GRANTED = "auth.granted"                  # Successful access
    ADMIN_OVERRIDE = "auth.admin_override"         # Admin bypass used
```

### 10.2 Immutable Audit Log

```python
# apps/core/models.py
class AuditLog(TenantModel):
    actor = models.CharField(max_length=128)        # user_id
    action = models.CharField(max_length=64)        # e.g. "source.create"
    resource_type = models.CharField(max_length=64) # e.g. "source"
    resource_id = models.CharField(max_length=128)  # e.g. "src-123"
    outcome = models.CharField(max_length=32)       # "allowed" | "denied"
    details = models.JSONField(default=dict)        # query, roles, permissions
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    realm = models.CharField(max_length=64, db_index=True)
    tenant_id = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Append-only, no updates, no deletes
        managed = True
        indexes = [
            models.Index(fields=["realm", "tenant_id", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["action", "outcome"]),
        ]
```

### 10.3 Compliance Mapping

| Standard | Requirement | RBAC Implementation |
|----------|-------------|---------------------|
| ISO 27001 A.9.1.1 | Access control policy | Role-based policy with realm boundaries |
| ISO 27001 A.9.1.2 | Access to networks | Network policies restrict by realm |
| ISO 27001 A.9.2.1 | User registration | Keycloak realm-scoped registration |
| ISO 27001 A.9.2.2 | User access provisioning | SpiceDB relationship provisioning |
| ISO 27001 A.9.2.3 | Removal of access | Keycloak deactivation + SpiceDB relationship deletion |
| ISO 27001 A.9.2.5 | Review of user access | Quarterly audit log analysis |
| ISO 27001 A.9.4.1 | Use of secret authentication | JWT RS256 + client secrets per realm |
| ISO 27001 A.9.4.2 | Secure log-on procedures | Keycloak brute-force protection |
| ISO 27001 A.12.4.1 | Event logging | Immutable audit log with RBAC decisions |
| SOC 2 CC6.1 | Logical access controls | Three-layer RBAC (role + tenant + SpiceDB) |
| SOC 2 CC6.2 | Access removal | Automated de-provisioning on role change |
| GDPR Art. 25 | Data protection by design | Tenant isolation + PII classifier |

---

## 11. KEYCLOAK REALM CONFIGURATION

### 11.1 Multi-Realm Setup

```yaml
# Keycloak realms are ISOLATED
realms:
  voyant-production:
    description: "Production realm"
    roles: [voyant-admin, voyant-engineer, voyant-analyst, voyant-viewer]
    clients: [voyant-api, voyant-mcp, voyant-web]
    
  voyant-staging:
    description: "Staging realm"
    roles: [voyant-admin, voyant-engineer, voyant-analyst, voyant-viewer]
    clients: [voyant-api, voyant-mcp, voyant-web]
    
  voyant-customer-a:
    description: "Customer A isolated realm"
    roles: [voyant-admin, voyant-engineer, voyant-analyst, voyant-viewer]
    clients: [voyant-api]
```

### 11.2 Realm-Specific Settings

```python
# voyant_project/security_settings.py
class SecuritySettings(BaseSettings):
    VOYANT_SECURITY_KEYCLOAK_URL: str = "http://keycloak:8080"
    VOYANT_SECURITY_KEYCLOAK_REALM: str = "voyant-production"
    VOYANT_SECURITY_KEYCLOAK_CLIENT_ID: str = "voyant-api"
    VOYANT_SECURITY_KEYCLOAK_CLIENT_SECRET: str = ""
    
    # Multi-realm support (optional)
    VOYANT_SECURITY_ALLOWED_REALMS: list[str] = ["voyant-production", "voyant-staging"]
```

---

## 12. IMPLEMENTATION CHECKLIST

### Phase 1: Foundation (Week 1)
- [ ] Add `realm` field to all models inheriting `TenantModel`
- [ ] Add `realm` field to `User` dataclass
- [ ] Update Keycloak auth to validate realm from JWT `iss` claim
- [ ] Update `require_role()` to check realm match
- [ ] Add `require_realm()` decorator
- [ ] Update `RBACManager` to filter by `realm + tenant_id`

### Phase 2: SpiceDB Enhancement (Week 2)
- [ ] Deploy updated `schema.zed` with tenant roles
- [ ] Create SpiceDB relationships for all existing users
- [ ] Implement `SpiceRBAC` class
- [ ] Add SpiceDB check to `enforce_access()`

### Phase 3: API Enforcement (Week 3)
- [ ] Add `auth=require_permission(...)` to ALL API endpoints
- [ ] Add role-based response filtering (hide fields viewers shouldn't see)
- [ ] Add RBAC to Milvus search (tenant + realm + owner filtering)
- [ ] Add RBAC to Octopus dispatcher
- [ ] Add RBAC to Deep Research workflow

### Phase 4: MCP Enforcement (Week 4)
- [ ] Add permission checks to ALL MCP tools
- [ ] Add role-based parameter validation (e.g., analysts can't set breadth > 3)
- [ ] Add MCP audit logging

### Phase 5: Audit & Compliance (Week 5)
- [ ] Immutable audit log migration
- [ ] RBAC audit event streaming to Kafka
- [ ] Compliance report generation
- [ ] Penetration testing (cross-tenant, cross-realm)

---

## 13. TESTING STRATEGY

### 13.1 RBAC Test Matrix

| Test | Viewer | Analyst | Engineer | Admin |
|------|--------|---------|----------|-------|
| Read own source | ❌ 403 | ✅ | ✅ | ✅ |
| Read other tenant source | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Read other realm source | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403* |
| Create source | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Delete source | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Execute SQL | ❌ 403 | ✅ | ✅ | ✅ |
| Write SQL (admin override) | ❌ 403 | ❌ 403 | ❌ 403 | ✅ (audited) |
| Index vectors | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Search vectors (own) | ❌ 403 | ✅ | ✅ | ✅ |
| Search vectors (other tenant) | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Scrape URL | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Deep research | ❌ 403 | ✅ (capped) | ✅ | ✅ |
| Read quotas | ❌ 403 | ❌ 403 | ✅ (own) | ✅ (all) |
| Read audit log | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Manage users | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |

*Admin can access other realms ONLY with explicit `manage:realms` permission AND explicit `?realm=` parameter.

### 13.2 Penetration Tests

| Attack Vector | Expected Defense |
|---------------|-----------------|
| JWT with forged roles | RS256 signature validation fails |
| JWT from wrong realm | Realm mismatch → 403 |
| Token without tenant_id | Defaults to "default" but still scoped |
| Replay old token | Expiration check fails |
| SQL injection in tenant_id | Parameterized queries prevent injection |
| IDOR (modify URL param to other tenant) | RBACManager filters by session tenant |
| Cross-realm API call | `require_realm()` blocks |
| Admin override without audit | Impossible — all overrides logged |

---

*End of Document*
