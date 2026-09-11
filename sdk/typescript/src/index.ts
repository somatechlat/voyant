/**
 * Voyant TypeScript/JavaScript SDK — Official client library for the Voyant Data Intelligence API.
 *
 * @example
 * ```ts
 * import { VoyantClient } from "@voyant/sdk";
 *
 * const client = new VoyantClient({
 *   baseUrl: "http://localhost:8000",
 *   token: "your-bearer-token",
 * });
 *
 * // Sources
 * const sources = await client.sources.list();
 * const source = await client.sources.create({
 *   name: "my-db",
 *   sourceType: "postgres",
 *   connectionConfig: { host: "localhost", port: 5432 },
 * });
 *
 * // Jobs
 * const jobs = await client.jobs.list();
 *
 * // Scraper
 * const result = await client.scraper.fetch({ url: "https://example.com" });
 *
 * // Ontology
 * const types = await client.ontology.listTypes();
 *
 * // ML
 * const models = await client.ml.listModels();
 *
 * // Governance
 * const results = await client.governance.search("customer_data");
 * ```
 *
 * @packageDocumentation
 */

// ===================================================================
// Types
// ===================================================================

/** Configuration options for the Voyant client. */
export interface VoyantClientOptions {
  /** Base URL of the Voyant API (e.g. "http://localhost:8000"). */
  baseUrl?: string;
  /** Bearer token for authentication. */
  token?: string;
  /** Default request timeout in milliseconds. */
  timeout?: number;
  /** Tenant ID (sent as X-Tenant-ID header). */
  tenantId?: string;
}

/** Error returned by the Voyant API. */
export class VoyantAPIError extends Error {
  public readonly statusCode: number;
  public readonly detail: unknown;

  constructor(message: string, statusCode: number, detail?: unknown) {
    super(message);
    this.name = "VoyantAPIError";
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

// ===================================================================
// Internal fetch helpers
// ===================================================================

interface FetchOptions {
  method: string;
  path: string;
  params?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
}

// ===================================================================
// Resource classes
// ===================================================================

/** Sources resource — manage data connectors. */
class SourcesResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  /** List all data sources. */
  async list(opts?: { limit?: number; offset?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/sources",
      params: { limit: opts?.limit ?? 100, offset: opts?.offset ?? 0 },
    })) as any[];
  }

  /** Get a single source by ID. */
  async get(sourceId: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/sources/${sourceId}` });
  }

  /** Create a new data source. */
  async create(opts: {
    name: string;
    sourceType: string;
    connectionConfig: Record<string, unknown>;
    credentials?: Record<string, unknown>;
    syncSchedule?: string;
  }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/sources",
      body: {
        name: opts.name,
        source_type: opts.sourceType,
        connection_config: opts.connectionConfig,
        ...(opts.credentials && { credentials: opts.credentials }),
        ...(opts.syncSchedule && { sync_schedule: opts.syncSchedule }),
      },
    });
  }

  /** Update a source. */
  async update(sourceId: string, body: Record<string, unknown>): Promise<any> {
    return await this.request({ method: "PUT", path: `/v1/sources/${sourceId}`, body });
  }

  /** Delete a source. */
  async delete(sourceId: string): Promise<any> {
    return await this.request({ method: "DELETE", path: `/v1/sources/${sourceId}` });
  }

  /** Discover source type from a hint. */
  async discover(hint: string): Promise<any> {
    return await this.request({ method: "POST", path: "/v1/sources/discover", body: { hint } });
  }

  /** Provision an Airbyte source connector. */
  async connect(opts: {
    sourceId: string;
    sourceDefinitionId: string;
    connectionConfig: Record<string, unknown>;
    destinationConfig?: Record<string, unknown>;
  }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/ingestion/connect",
      body: {
        source_id: opts.sourceId,
        source_definition_id: opts.sourceDefinitionId,
        connection_config: opts.connectionConfig,
        ...(opts.destinationConfig && { destination_config: opts.destinationConfig }),
      },
    });
  }
}

/** Jobs resource — manage async data jobs. */
class JobsResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async list(opts?: { status?: string; jobType?: string; limit?: number; offset?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/jobs",
      params: {
        limit: opts?.limit ?? 50,
        offset: opts?.offset ?? 0,
        ...(opts?.status && { status: opts.status }),
        ...(opts?.jobType && { job_type: opts.jobType }),
      },
    })) as any[];
  }

  async get(jobId: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/jobs/${jobId}` });
  }

  async cancel(jobId: string): Promise<any> {
    return await this.request({ method: "POST", path: `/v1/jobs/${jobId}/cancel` });
  }

  async ingest(opts: { sourceId: string; tables?: string[]; mode?: string }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/jobs/ingest",
      body: {
        source_id: opts.sourceId,
        mode: opts.mode ?? "full",
        ...(opts.tables && { tables: opts.tables }),
      },
    });
  }

  async profile(opts: { sourceId: string; table?: string; sampleSize?: number }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/jobs/profile",
      body: {
        source_id: opts.sourceId,
        sample_size: opts.sampleSize ?? 10000,
        ...(opts.table && { table: opts.table }),
      },
    });
  }

  async quality(opts: { sourceId: string; table?: string; checks?: string[] }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/jobs/quality",
      body: {
        source_id: opts.sourceId,
        ...(opts.table && { table: opts.table }),
        ...(opts.checks && { checks: opts.checks }),
      },
    });
  }

  async analyze(opts: {
    sourceId?: string;
    table?: string;
    tables?: string[];
    analyzers?: string[];
    kpis?: Array<{ name: string; sql: string }>;
    sampleSize?: number;
  }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/analyze",
      body: {
        sample_size: opts.sampleSize ?? 10000,
        profile: true,
        run_analyzers: true,
        generate_artifacts: true,
        ...(opts.sourceId && { source_id: opts.sourceId }),
        ...(opts.table && { table: opts.table }),
        ...(opts.tables && { tables: opts.tables }),
        ...(opts.analyzers && { analyzers: opts.analyzers }),
        ...(opts.kpis && { kpis: opts.kpis }),
      },
    });
  }
}

/** SQL resource — execute queries and explore tables. */
class SQLResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async tables(): Promise<any[]> {
    return (await this.request({ method: "GET", path: "/v1/sql/tables" })) as any[];
  }

  async columns(table: string): Promise<any[]> {
    return (await this.request({ method: "GET", path: `/v1/sql/tables/${table}/columns` })) as any[];
  }

  async query(sql: string, opts?: { maxRows?: number }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/sql/query",
      body: { sql, max_rows: opts?.maxRows ?? 1000 },
    });
  }
}

/** Ontology resource — manage types, objects, links, actions, functions. */
class OntologyResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async listTypes(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ontology/types",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async getType(typeId: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/ontology/types/${typeId}` });
  }

  async createType(opts: { name: string; description?: string; properties?: any[] }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/ontology/types",
      body: {
        name: opts.name,
        description: opts.description ?? "",
        ...(opts.properties && { properties: opts.properties }),
      },
    });
  }

  async updateType(typeId: string, body: Record<string, unknown>): Promise<any> {
    return await this.request({ method: "PUT", path: `/v1/ontology/types/${typeId}`, body });
  }

  async deleteType(typeId: string): Promise<any> {
    return await this.request({ method: "DELETE", path: `/v1/ontology/types/${typeId}` });
  }

  async listObjects(opts?: { typeId?: string; limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ontology/objects",
      params: {
        limit: opts?.limit ?? 100,
        ...(opts?.typeId && { object_type_id: opts.typeId }),
      },
    })) as any[];
  }

  async getObject(objectId: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/ontology/objects/${objectId}` });
  }

  async createObject(opts: { objectTypeId: string; properties?: Record<string, unknown> }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/ontology/objects",
      body: {
        object_type_id: opts.objectTypeId,
        ...(opts.properties && { properties: opts.properties }),
      },
    });
  }

  async updateObject(objectId: string, body: Record<string, unknown>): Promise<any> {
    return await this.request({ method: "PUT", path: `/v1/ontology/objects/${objectId}`, body });
  }

  async deleteObject(objectId: string): Promise<any> {
    return await this.request({ method: "DELETE", path: `/v1/ontology/objects/${objectId}` });
  }

  async listLinks(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ontology/links",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async createLink(opts: {
    linkTypeId: string;
    sourceObjectId: string;
    targetObjectId: string;
    properties?: Record<string, unknown>;
  }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/ontology/links",
      body: {
        link_type_id: opts.linkTypeId,
        source_object_id: opts.sourceObjectId,
        target_object_id: opts.targetObjectId,
        ...(opts.properties && { properties: opts.properties }),
      },
    });
  }

  async deleteLink(linkId: string): Promise<any> {
    return await this.request({ method: "DELETE", path: `/v1/ontology/links/${linkId}` });
  }

  async listLinkTypes(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ontology/link-types",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async listActions(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ontology/actions",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async listFunctions(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ontology/functions",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async listInterfaces(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ontology/interfaces",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }
}

/** Scraper resource — web scraping, OCR, PDF, transcription. */
class ScraperResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async startScrape(opts: {
    urls: string[];
    selectors?: Record<string, unknown>;
    options?: Record<string, unknown>;
  }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/scrape/start",
      body: {
        urls: opts.urls,
        ...(opts.selectors && { selectors: opts.selectors }),
        ...(opts.options && { options: opts.options }),
      },
    });
  }

  async getStatus(jobId: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/scrape/status/${jobId}` });
  }

  async getResult(jobId: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/scrape/result/${jobId}` });
  }

  async cancelScrape(jobId: string): Promise<any> {
    return await this.request({ method: "POST", path: "/v1/scrape/cancel", body: { job_id: jobId } });
  }

  async fetch(opts: {
    url: string;
    engine?: string;
    waitFor?: string;
    scroll?: boolean;
    timeout?: number;
    waitUntil?: string;
    settleMs?: number;
    blockResources?: boolean;
    captureJson?: boolean;
  }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/scrape/fetch",
      body: {
        url: opts.url,
        engine: opts.engine ?? "playwright",
        scroll: opts.scroll ?? false,
        timeout: opts.timeout ?? 30,
        ...(opts.waitFor && { wait_for: opts.waitFor }),
        ...(opts.waitUntil && { wait_until: opts.waitUntil }),
        ...(opts.settleMs !== undefined && { settle_ms: opts.settleMs }),
        ...(opts.blockResources !== undefined && { block_resources: opts.blockResources }),
        ...(opts.captureJson && { capture_json: opts.captureJson }),
      },
    });
  }

  async extract(opts: { html: string; selectors: Record<string, unknown> }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/scrape/extract",
      body: { html: opts.html, selectors: opts.selectors },
    });
  }

  async ocr(opts: { imageUrl: string; language?: string }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/scrape/ocr",
      body: { image_url: opts.imageUrl, language: opts.language ?? "spa+eng" },
    });
  }

  async parsePdf(opts: { pdfUrl: string; extractTables?: boolean }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/scrape/parse_pdf",
      body: { pdf_url: opts.pdfUrl, extract_tables: opts.extractTables ?? false },
    });
  }

  async transcribe(opts: { mediaUrl: string; language?: string }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/scrape/transcribe",
      body: { media_url: opts.mediaUrl, language: opts.language ?? "es" },
    });
  }

  async captchaStatus(): Promise<any> {
    return await this.request({ method: "GET", path: "/v1/scrape/captcha/status" });
  }

  async captchaTest(opts: {
    captchaType?: string;
    siteKey: string;
    pageUrl: string;
    action?: string;
  }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/scrape/captcha/test",
      body: {
        captcha_type: opts.captchaType ?? "recaptcha_v2",
        site_key: opts.siteKey,
        page_url: opts.pageUrl,
        ...(opts.action && { action: opts.action }),
      },
    });
  }

  async health(): Promise<any> {
    return await this.request({ method: "GET", path: "/v1/scrape/health" });
  }
}

/** ML Platform resource — models, experiments, agents. */
class MLResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async listModels(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ml/models",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async getModel(modelId: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/ml/models/${modelId}` });
  }

  async createModel(opts: { name: string; description?: string }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/ml/models",
      body: { name: opts.name, description: opts.description ?? "" },
    });
  }

  async listExperiments(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ml/experiments",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async createExperiment(opts: { name: string }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/ml/experiments",
      body: { name: opts.name },
    });
  }

  async listAgents(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ml/agents",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }

  async createAgent(opts: { name: string }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/ml/agents",
      body: { name: opts.name },
    });
  }

  async deleteAgent(agentId: string): Promise<any> {
    return await this.request({ method: "DELETE", path: `/v1/ml/agents/${agentId}` });
  }

  async listEndpoints(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/ml/endpoints",
      params: { limit: opts?.limit ?? 100 },
    })) as any[];
  }
}

/** Governance resource — lineage, schemas, quotas, policies. */
class GovernanceResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async search(query: string, opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/governance/search",
      params: { q: query, limit: opts?.limit ?? 20 },
    })) as any[];
  }

  async lineage(urn: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/governance/lineage/${urn}` });
  }

  async schema(urn: string): Promise<any> {
    return await this.request({ method: "GET", path: `/v1/governance/schema/${urn}` });
  }

  async listClassifications(): Promise<any[]> {
    return (await this.request({ method: "GET", path: "/v1/governance/classifications" })) as any[];
  }

  async quotaTiers(): Promise<any[]> {
    return (await this.request({ method: "GET", path: "/v1/governance/quotas/tiers" })) as any[];
  }

  async quotaUsage(): Promise<any> {
    return await this.request({ method: "GET", path: "/v1/governance/quotas/usage" });
  }
}

/** Auth resource — login, logout, refresh, current user. */
class AuthResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async login(opts: { username: string; password: string }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/auth/login",
      body: { username: opts.username, password: opts.password },
    });
  }

  async logout(): Promise<any> {
    return await this.request({ method: "POST", path: "/v1/auth/logout" });
  }

  async refresh(refreshToken: string): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/auth/refresh",
      body: { refresh_token: refreshToken },
    });
  }

  async me(): Promise<any> {
    return await this.request({ method: "GET", path: "/v1/auth/me" });
  }
}

/** Search resource — vector and full-text search. */
class SearchResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async index(opts: { text: string; itemId?: string; metadata?: Record<string, unknown> }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/search/index",
      body: {
        text: opts.text,
        ...(opts.itemId && { item_id: opts.itemId }),
        ...(opts.metadata && { metadata: opts.metadata }),
      },
    });
  }

  async query(opts: { query: string; limit?: number }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/search/query",
      body: { query: opts.query, limit: opts.limit ?? 10 },
    });
  }

  async deleteItem(itemId: string): Promise<any> {
    return await this.request({ method: "DELETE", path: `/v1/search/${itemId}` });
  }
}

/** Capsules resource — Intelligence Recipes lifecycle. */
class CapsulesResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async registry(): Promise<any[]> {
    return (await this.request({ method: "GET", path: "/v1/capsules/registry" })) as any[];
  }

  async create(opts: { name: string; [key: string]: unknown }): Promise<any> {
    return await this.request({ method: "POST", path: "/v1/capsules/create", body: opts });
  }

  async install(opts: { capsuleId: string; parameterOverrides?: Record<string, unknown> }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/capsules/install",
      body: {
        capsule_id: opts.capsuleId,
        ...(opts.parameterOverrides && { parameter_overrides: opts.parameterOverrides }),
      },
    });
  }

  async installed(): Promise<any[]> {
    return (await this.request({ method: "GET", path: "/v1/capsules/installed" })) as any[];
  }

  async run(opts: { installationId: string; parameterValues?: Record<string, unknown> }): Promise<any> {
    return await this.request({
      method: "POST",
      path: "/v1/capsules/run",
      body: {
        installation_id: opts.installationId,
        ...(opts.parameterValues && { parameter_values: opts.parameterValues }),
      },
    });
  }

  async uninstall(installationId: string): Promise<any> {
    return await this.request({ method: "DELETE", path: `/v1/capsules/installed/${installationId}` });
  }
}

/** Admin resource — dashboard, settings, audit. */
class AdminResource {
  constructor(private readonly request: (opts: FetchOptions) => Promise<unknown>) {}

  async dashboard(): Promise<any> {
    return await this.request({ method: "GET", path: "/v1/admin/dashboard" });
  }

  async listTenants(): Promise<any[]> {
    return (await this.request({ method: "GET", path: "/v1/admin/tenants" })) as any[];
  }

  async settings(): Promise<any> {
    return await this.request({ method: "GET", path: "/v1/admin/settings" });
  }

  async auditLog(opts?: { limit?: number }): Promise<any[]> {
    return (await this.request({
      method: "GET",
      path: "/v1/admin/audit",
      params: { limit: opts?.limit ?? 50 },
    })) as any[];
  }
}

// ===================================================================
// Main Client
// ===================================================================

/**
 * Voyant API client.
 *
 * @example
 * ```ts
 * const client = new VoyantClient({
 *   baseUrl: "http://localhost:8000",
 *   token: "your-bearer-token",
 * });
 *
 * const sources = await client.sources.list();
 * ```
 */
export class VoyantClient {
  private readonly baseUrl: string;
  private readonly token: string;
  private readonly timeout: number;
  private readonly tenantId: string;

  /** Data sources. */
  public readonly sources: SourcesResource;
  /** Async jobs. */
  public readonly jobs: JobsResource;
  /** SQL queries. */
  public readonly sql: SQLResource;
  /** Ontology (types, objects, links). */
  public readonly ontology: OntologyResource;
  /** Web scraper. */
  public readonly scraper: ScraperResource;
  /** ML platform. */
  public readonly ml: MLResource;
  /** Data governance. */
  public readonly governance: GovernanceResource;
  /** Authentication. */
  public readonly auth: AuthResource;
  /** Vector/full-text search. */
  public readonly search: SearchResource;
  /** Intelligence Recipes / Capsules. */
  public readonly capsules: CapsulesResource;
  /** Admin panel. */
  public readonly admin: AdminResource;

  constructor(options: VoyantClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? "http://localhost:8000").replace(/\/+$/, "");
    this.token = options.token ?? "";
    this.timeout = options.timeout ?? 60_000;
    this.tenantId = options.tenantId ?? "";

    const req = this._request.bind(this);
    this.sources = new SourcesResource(req);
    this.jobs = new JobsResource(req);
    this.sql = new SQLResource(req);
    this.ontology = new OntologyResource(req);
    this.scraper = new ScraperResource(req);
    this.ml = new MLResource(req);
    this.governance = new GovernanceResource(req);
    this.auth = new AuthResource(req);
    this.search = new SearchResource(req);
    this.capsules = new CapsulesResource(req);
    this.admin = new AdminResource(req);
  }

  /** Build headers for each request. */
  private _headers(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    if (this.tenantId) {
      headers["X-Tenant-ID"] = this.tenantId;
    }
    return headers;
  }

  /** Core request method using fetch. */
  private async _request(opts: FetchOptions): Promise<unknown> {
    let url = `${this.baseUrl}${opts.path}`;

    // Append query params
    if (opts.params) {
      const filtered = Object.fromEntries(
        Object.entries(opts.params).filter(([, v]) => v !== undefined),
      );
      if (Object.keys(filtered).length > 0) {
        const qs = new URLSearchParams(
          Object.entries(filtered).map(([k, v]) => [k, String(v)]),
        ).toString();
        url += `?${qs}`;
      }
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(url, {
        method: opts.method,
        headers: this._headers(),
        body: opts.body ? JSON.stringify(opts.body) : undefined,
        signal: controller.signal,
      });

      if (resp.status === 204) return null;

      const data = await resp.json().catch(() => null);

      if (!resp.ok) {
        throw new VoyantAPIError(
          `API error ${resp.status}: ${JSON.stringify(data)}`,
          resp.status,
          data,
        );
      }

      return data;
    } finally {
      clearTimeout(timer);
    }
  }

  /** Check API health. */
  async health(): Promise<any> {
    const resp = await fetch(`${this.baseUrl}/health`);
    return resp.json();
  }
}

export default VoyantClient;
