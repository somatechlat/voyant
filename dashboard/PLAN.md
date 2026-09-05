# Voyant Admin Dashboard — Implementation Plan

## Architecture

- **Stack**: Lit 3 + Vite + Tailwind CDN (extend existing `dashboard/`)
- **API**: All data from `GET/POST/PUT/DELETE /v1/admin/*` (already built)
- **Auth**: Real JWT via Keycloak — stored in localStorage, attached to all API calls
- **Routing**: `@lit-labs/router` (already imported)
- **State**: Component-level `@state()` — no external state library needed for this scope

## Shared Infrastructure (build first)

| Component | File | Purpose |
|-----------|------|---------|
| API Client | `src/lib/api.ts` | Fetch wrapper with auth headers, error handling, base URL |
| Auth Guard | `src/lib/auth.ts` | JWT storage, validation, login/logout, role check |
| Sidebar | `src/components/saas-sidebar.ts` | Navigation sidebar with route links and active state |
| Topbar | `src/components/saas-topbar.ts` | Header with user info, tenant selector, notifications |
| Data Table | `src/components/saas-data-table.ts` | Reusable table with sorting, filtering, pagination |
| Stat Card | `src/components/saas-stat-card.ts` | Metric display card (number + label + trend) |
| Toast | `src/components/saas-toast.ts` | Notification toast |

## Pages (priority order)

| # | Route | View | Key Features |
|---|-------|------|-------------|
| 1 | `/admin/login` | Login | Real Keycloak JWT auth |
| 2 | `/admin` | Dashboard | System health, stats grid, service status |
| 3 | `/admin/jobs` | Jobs | Filterable table, cancel/reset actions, detail drawer |
| 4 | `/admin/sources` | Sources | CRUD, connection test, status |
| 5 | `/admin/governance` | Governance | Policies, contracts, quotas tabs |
| 6 | `/admin/capsules` | Capsules | Lifecycle management, install/execute |
| 7 | `/admin/ontology` | Ontology | Object types, properties, links tree |
| 8 | `/admin/audit` | Audit Log | Filtered search, export |
| 9 | `/admin/sql` | SQL Console | Query editor, results table, history |
| 10 | `/admin/search` | Search | Index management, test queries |
| 11 | `/admin/scraper` | Scraper | Job monitoring, artifact browser |
| 12 | `/admin/settings` | Settings | System settings CRUD |
| 13 | `/admin/tenants` | Tenants | Tenant list, quota management |

## Build Order

1. API client + Auth guard
2. Sidebar + Topbar (shell)
3. Dashboard page (proves the full stack works)
4. Jobs page (most used by operators)
5. Remaining pages (can be parallelized)

## Design Tokens (from existing tailwind.config.ts)

- Background: `bg-saas-page` (#f5f5f5)
- Cards: `bg-white` with `border border-gray-100`
- Text: `text-saas-text` (#1a1a1a)
- Success: `text-saas-success` (#22c55e)
- Font: Geist
- Border radius: `rounded-xl`
- Shadows: `shadow-sm` on cards, `shadow-md` on hover
