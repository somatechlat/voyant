package com.voyant.sdk;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Official Java SDK client for the Voyant Data Intelligence API.
 *
 * <p>Usage:</p>
 * <pre>{@code
 * VoyantClient client = new VoyantClient("http://localhost:8000", "your-api-key");
 * var types = client.ontology().listTypes(100);
 * var models = client.ml().listModels(100);
 * var tasks = client.scraper().listTasks(100);
 * }</pre>
 */
public class VoyantClient implements AutoCloseable {

    private static final String DEFAULT_BASE_URL = "http://localhost:8000";
    private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(60);
    private static final String USER_AGENT = "voyant-java-sdk/1.0.0";

    private final HttpClient httpClient;
    private final String baseURL;
    private final String apiKey;
    private final String tenantID;
    private final ObjectMapper objectMapper;

    private final OntologyService ontologyService;
    private final MLService mlService;
    private final ScraperService scraperService;

    /**
     * Creates a new VoyantClient.
     *
     * @param baseURL Base URL of the Voyant API
     * @param apiKey  API key for authentication
     */
    public VoyantClient(String baseURL, String apiKey) {
        this(baseURL, apiKey, null, DEFAULT_TIMEOUT);
    }

    /**
     * Creates a new VoyantClient with full configuration.
     *
     * @param baseURL  Base URL of the Voyant API
     * @param apiKey   API key for authentication
     * @param tenantID Optional tenant ID
     * @param timeout  HTTP request timeout
     */
    public VoyantClient(String baseURL, String apiKey, String tenantID, Duration timeout) {
        this.baseURL = baseURL != null ? baseURL.replaceAll("/+$", "") : DEFAULT_BASE_URL;
        this.apiKey = apiKey;
        this.tenantID = tenantID;
        this.objectMapper = new ObjectMapper();
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(timeout != null ? timeout : DEFAULT_TIMEOUT)
                .build();

        this.ontologyService = new OntologyService(this);
        this.mlService = new MLService(this);
        this.scraperService = new ScraperService(this);
    }

    // ── Service accessors ─────────────────────────────────────────────────

    /** Returns the Ontology service for type/object/link CRUD. */
    public OntologyService ontology() { return ontologyService; }

    /** Returns the ML service for models/experiments/agents. */
    public MLService ml() { return mlService; }

    /** Returns the Scraper service for web scraping operations. */
    public ScraperService scraper() { return scraperService; }

    /** Checks API health. */
    public Map<String, Object> health() throws IOException, InterruptedException {
        return get("/health", new TypeReference<>() {});
    }

    // ── Internal HTTP helpers ─────────────────────────────────────────────

    ObjectMapper mapper() { return objectMapper; }

    private String buildQueryString(Map<String, String> params) {
        if (params == null || params.isEmpty()) return "";
        return "?" + params.entrySet().stream()
                .filter(e -> e.getValue() != null)
                .map(e -> URLEncoder.encode(e.getKey(), StandardCharsets.UTF_8)
                        + "=" + URLEncoder.encode(e.getValue(), StandardCharsets.UTF_8))
                .collect(Collectors.joining("&"));
    }

    private HttpRequest.Builder requestBuilder(String path) {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(baseURL + path))
                .header("Content-Type", "application/json")
                .header("User-Agent", USER_AGENT);
        if (apiKey != null && !apiKey.isEmpty()) {
            builder.header("Authorization", "Bearer " + apiKey);
        }
        if (tenantID != null && !tenantID.isEmpty()) {
            builder.header("X-Tenant-ID", tenantID);
        }
        return builder;
    }

    <T> T get(String path, Map<String, String> params, TypeReference<T> typeRef)
            throws IOException, InterruptedException {
        String fullPath = path + buildQueryString(params);
        HttpRequest request = requestBuilder(fullPath).GET().build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 400) {
            throw new VoyantAPIException(response.statusCode(), response.body());
        }
        if (response.statusCode() == 204) return null;
        return objectMapper.readValue(response.body(), typeRef);
    }

    <T> T get(String path, TypeReference<T> typeRef) throws IOException, InterruptedException {
        return get(path, null, typeRef);
    }

    <T> T post(String path, Object body, TypeReference<T> typeRef)
            throws IOException, InterruptedException {
        String jsonBody = body != null ? objectMapper.writeValueAsString(body) : "{}";
        HttpRequest request = requestBuilder(path)
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 400) {
            throw new VoyantAPIException(response.statusCode(), response.body());
        }
        if (response.statusCode() == 204) return null;
        return objectMapper.readValue(response.body(), typeRef);
    }

    <T> T put(String path, Object body, TypeReference<T> typeRef)
            throws IOException, InterruptedException {
        String jsonBody = body != null ? objectMapper.writeValueAsString(body) : "{}";
        HttpRequest request = requestBuilder(path)
                .PUT(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 400) {
            throw new VoyantAPIException(response.statusCode(), response.body());
        }
        if (response.statusCode() == 204) return null;
        return objectMapper.readValue(response.body(), typeRef);
    }

    void delete(String path) throws IOException, InterruptedException {
        HttpRequest request = requestBuilder(path).DELETE().build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 400) {
            throw new VoyantAPIException(response.statusCode(), response.body());
        }
    }

    @Override
    public void close() {
        // HttpClient doesn't implement Closeable in all JDK versions,
        // but we can attempt cleanup.
    }
}
