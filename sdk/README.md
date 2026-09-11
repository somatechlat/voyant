# Voyant SDK

Official client libraries for the [Voyant](https://github.com/your-org/voyant) Data Intelligence API.

## Python SDK

### Installation

```bash
pip install httpx  # only dependency
```

Copy `sdk/python/voyant/` into your project or install from the repo:

```bash
pip install -e sdk/python/
```

### Quick Start

```python
from voyant import VoyantClient

client = VoyantClient(
    base_url="http://localhost:8000",
    token="your-bearer-token",
    tenant_id="my-tenant",  # optional
)

# ── Sources ──────────────────────────────────────────
sources = client.sources.list()
source = client.sources.create(
    name="production-db",
    source_type="postgres",
    connection_config={"host": "db.example.com", "port": 5432, "database": "analytics"},
)
discovered = client.sources.discover("postgresql://db.example.com/analytics")

# ── Jobs ─────────────────────────────────────────────
jobs = client.jobs.list(status="running")
job = client.jobs.get("job-id-123")
client.jobs.cancel("job-id-123")

# Run data profiling
result = client.jobs.profile(source_id="src-123", table="users")

# Run full analysis
analysis = client.jobs.analyze(
    source_id="src-123",
    tables=["users", "orders"],
    kpis=[{"name": "revenue", "sql": "SELECT SUM(amount) FROM orders"}],
)

# ── SQL ──────────────────────────────────────────────
tables = client.sql.tables()
result = client.sql.query("SELECT * FROM users LIMIT 10")

# ── Scraper ──────────────────────────────────────────
# Fetch a page
page = client.scraper.fetch(url="https://example.com", engine="playwright")

# Extract data from HTML
data = client.scraper.extract(
    html="<html>...</html>",
    selectors={"titles": "h1.title", "prices": "span.price"},
)

# Start a scrape job
job = client.scraper.start_scrape(
    urls=["https://example.com/page1", "https://example.com/page2"],
    selectors={"heading": "h1", "content": "article"},
)

# OCR
text = client.scraper.ocr(image_url="https://example.com/image.png")

# PDF parsing
pdf_data = client.scraper.parse_pdf(pdf_url="https://example.com/doc.pdf")

# CAPTCHA solver status
captcha = client.scraper.captcha_status()
# Test CAPTCHA solver
test_result = client.scraper.captcha_test(
    captcha_type="recaptcha_v2",
    site_key="6Le...",
    page_url="https://example.com/login",
)

# Scraper health check
health = client.scraper.health()

# ── Ontology ─────────────────────────────────────────
types = client.ontology.list_types()
new_type = client.ontology.create_type(name="Customer", description="A customer entity")

objects = client.ontology.list_objects(type_id="type-123")
new_obj = client.ontology.create_object(
    object_type_id="type-123",
    properties={"name": "Acme Corp", "industry": "Tech"},
)

# Create links between objects
link = client.ontology.create_link(
    link_type_id="lt-purchased",
    source_object_id="obj-customer-1",
    target_object_id="obj-product-42",
)

# Traverse graph
graph = client.ontology.traverse("obj-customer-1", depth=3)

# ── ML Platform ──────────────────────────────────────
models = client.ml.list_models()
model = client.ml.create_model(name="churn-predictor", description="Predicts customer churn")
experiments = client.ml.list_experiments()
agents = client.ml.list_agents()

# ── Governance ───────────────────────────────────────
results = client.governance.search("customer_data")
lineage = client.governance.lineage("urn:li:dataset:snowflake.analytics.users")
schema = client.governance.schema("urn:li:dataset:snowflake.analytics.users")
usage = client.governance.quota_usage()

# ── Auth ─────────────────────────────────────────────
auth_resp = client.auth.login(username="admin", password="secret")
me = client.auth.me()

# ── Search ───────────────────────────────────────────
indexed = client.search.index(text="Customer segmentation analysis", metadata={"type": "report"})
results = client.search.query(query="segmentation", limit=5)

# ── Capsules ─────────────────────────────────────────
registry = client.capsules.registry()
installed = client.capsules.installed()

# ── Error Handling ───────────────────────────────────
from voyant.client import VoyantAPIError

try:
    client.jobs.get("nonexistent")
except VoyantAPIError as e:
    print(f"Status: {e.status_code}, Detail: {e.detail}")

# ── Context Manager ──────────────────────────────────
with VoyantClient(base_url="http://localhost:8000", token="tok") as client:
    sources = client.sources.list()
# HTTP connection is automatically closed
```

---

## TypeScript SDK

### Installation

Copy `sdk/typescript/src/index.ts` into your project.

### Quick Start

```typescript
import { VoyantClient } from "./voyant-sdk";

const client = new VoyantClient({
  baseUrl: "http://localhost:8000",
  token: "your-bearer-token",
  tenantId: "my-tenant", // optional
});

// ── Sources ──────────────────────────────────────────
const sources = await client.sources.list();
const source = await client.sources.create({
  name: "production-db",
  sourceType: "postgres",
  connectionConfig: { host: "db.example.com", port: 5432, database: "analytics" },
});

// ── Jobs ─────────────────────────────────────────────
const jobs = await client.jobs.list({ status: "running" });
const job = await client.jobs.get("job-id-123");
await client.jobs.cancel("job-id-123");

// Data profiling
const profile = await client.jobs.profile({ sourceId: "src-123", table: "users" });

// Full analysis
const analysis = await client.jobs.analyze({
  sourceId: "src-123",
  tables: ["users", "orders"],
  kpis: [{ name: "revenue", sql: "SELECT SUM(amount) FROM orders" }],
});

// ── SQL ──────────────────────────────────────────────
const tables = await client.sql.tables();
const result = await client.sql.query("SELECT * FROM users LIMIT 10");

// ── Scraper ──────────────────────────────────────────
const page = await client.scraper.fetch({ url: "https://example.com", engine: "playwright" });
const data = await client.scraper.extract({
  html: "<html>...</html>",
  selectors: { titles: "h1.title", prices: "span.price" },
});
const captchaStatus = await client.scraper.captchaStatus();
const scraperHealth = await client.scraper.health();

// ── Ontology ─────────────────────────────────────────
const types = await client.ontology.listTypes();
const newObj = await client.ontology.createObject({
  objectTypeId: "type-123",
  properties: { name: "Acme Corp", industry: "Tech" },
});
const links = await client.ontology.listLinks();

// ── ML Platform ──────────────────────────────────────
const models = await client.ml.listModels();
const experiments = await client.ml.listExperiments();

// ── Governance ───────────────────────────────────────
const searchResults = await client.governance.search("customer_data");
const lineage = await client.governance.lineage("urn:li:dataset:...");

// ── Auth ─────────────────────────────────────────────
const auth = await client.auth.login({ username: "admin", password: "secret" });
const user = await client.auth.me();

// ── Search ───────────────────────────────────────────
await client.search.index({ text: "Customer segmentation analysis" });
const results = await client.search.query({ query: "segmentation", limit: 5 });

// ── Error Handling ───────────────────────────────────
import { VoyantAPIError } from "./voyant-sdk";

try {
  await client.jobs.get("nonexistent");
} catch (e) {
  if (e instanceof VoyantAPIError) {
    console.error(`Status: ${e.statusCode}, Detail:`, e.detail);
  }
}
```

---

## SDK Architecture

Both SDKs follow the same pattern:

| Feature | Description |
|---------|-------------|
| **Resource namespaces** | `.sources`, `.jobs`, `.scraper`, `.ontology`, `.ml`, `.governance`, `.auth`, `.search`, `.capsules`, `.admin` |
| **Authentication** | Bearer token passed via `Authorization` header |
| **Multi-tenancy** | Optional `X-Tenant-ID` header |
| **Error handling** | Custom error class with status code + detail body |
| **Pagination** | `limit`/`offset` params on list endpoints |
| **Timeout** | Configurable per-client |

## API Reference

The full API surface is defined in `docs/api/openapi.json`. Key areas:

| Area | Prefix | Description |
|------|--------|-------------|
| Sources | `/v1/sources` | Data connectors (Postgres, S3, API, etc.) |
| Jobs | `/v1/jobs` | Async data jobs (ingest, profile, quality, analyze) |
| SQL | `/v1/sql` | Direct SQL query execution |
| Scraper | `/v1/scrape` | Web scraping, OCR, PDF, transcription, CAPTCHA |
| Ontology | `/v1/ontology` | Type system, objects, links, actions, functions |
| ML | `/v1/ml` | Models, experiments, agents, endpoints |
| Governance | `/v1/governance` | Lineage, schemas, quotas, policies |
| Auth | `/v1/auth` | Login, logout, token refresh |
| Search | `/v1/search` | Vector and full-text search |
| Capsules | `/v1/capsules` | Intelligence Recipes lifecycle |
| Admin | `/v1/admin` | Dashboard, settings, audit, tenants |
