package com.voyant.sdk;

import com.fasterxml.jackson.core.type.TypeReference;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * ML Platform service — models, experiments, runs, agents, and endpoints.
 *
 * <p>Usage:</p>
 * <pre>{@code
 * MLService ml = client.ml();
 * List<Map<String, Object>> models = ml.listModels(100);
 * Map<String, Object> experiment = ml.createExperiment("experiment-1");
 * Map<String, Object> run = ml.createRun("exp-id", Map.of("lr", 0.01));
 * }</pre>
 */
public class MLService {

    private static final TypeReference<List<Map<String, Object>>> LIST_MAP =
            new TypeReference<>() {};
    private static final TypeReference<Map<String, Object>> MAP =
            new TypeReference<>() {};

    private final VoyantClient client;

    MLService(VoyantClient client) {
        this.client = client;
    }

    // ── Models ───────────────────────────────────────────────────────────

    /** Lists all registered ML models. */
    public List<Map<String, Object>> listModels(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ml/models", params, LIST_MAP);
    }

    /** Gets a single ML model by ID. */
    public Map<String, Object> getModel(String modelId) throws IOException, InterruptedException {
        return client.get("/v1/ml/models/" + modelId, MAP);
    }

    /** Creates a new ML model registry entry. */
    public Map<String, Object> createModel(String name, String description) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("name", name);
        body.put("description", description != null ? description : "");
        return client.post("/v1/ml/models", body, MAP);
    }

    /** Creates a new version for an existing model. */
    public Map<String, Object> createModelVersion(String modelId, Map<String, Object> params) throws IOException, InterruptedException {
        return client.post("/v1/ml/models/" + modelId + "/versions", params != null ? params : Map.of(), MAP);
    }

    /** Promotes a model version to a specific stage. */
    public Map<String, Object> setModelStage(String versionId, String stage) throws IOException, InterruptedException {
        return client.put("/v1/ml/model-versions/" + versionId + "/stage", Map.of("stage", stage), MAP);
    }

    // ── Experiments ──────────────────────────────────────────────────────

    /** Lists all experiments. */
    public List<Map<String, Object>> listExperiments(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ml/experiments", params, LIST_MAP);
    }

    /** Gets a single experiment by ID. */
    public Map<String, Object> getExperiment(String experimentId) throws IOException, InterruptedException {
        return client.get("/v1/ml/experiments/" + experimentId, MAP);
    }

    /** Creates a new experiment. */
    public Map<String, Object> createExperiment(String name) throws IOException, InterruptedException {
        return client.post("/v1/ml/experiments", Map.of("name", name), MAP);
    }

    /** Creates a new run within an experiment. */
    public Map<String, Object> createRun(String experimentId, Map<String, Object> params) throws IOException, InterruptedException {
        return client.post("/v1/ml/experiments/" + experimentId + "/runs", params != null ? params : Map.of(), MAP);
    }

    /** Logs metrics for a specific run. */
    public Map<String, Object> logMetrics(String runId, Map<String, Object> metrics) throws IOException, InterruptedException {
        return client.put("/v1/ml/runs/" + runId + "/metrics", metrics, MAP);
    }

    // ── Agents ───────────────────────────────────────────────────────────

    /** Lists all ML agents. */
    public List<Map<String, Object>> listAgents(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ml/agents", params, LIST_MAP);
    }

    /** Gets a single agent by ID. */
    public Map<String, Object> getAgent(String agentId) throws IOException, InterruptedException {
        return client.get("/v1/ml/agents/" + agentId, MAP);
    }

    /** Creates a new ML agent. */
    public Map<String, Object> createAgent(String name) throws IOException, InterruptedException {
        return client.post("/v1/ml/agents", Map.of("name", name), MAP);
    }

    /** Updates an existing agent. */
    public Map<String, Object> updateAgent(String agentId, Map<String, Object> updates) throws IOException, InterruptedException {
        return client.put("/v1/ml/agents/" + agentId, updates, MAP);
    }

    /** Deletes an agent. */
    public void deleteAgent(String agentId) throws IOException, InterruptedException {
        client.delete("/v1/ml/agents/" + agentId);
    }

    // ── Endpoints ────────────────────────────────────────────────────────

    /** Lists all ML serving endpoints. */
    public List<Map<String, Object>> listEndpoints(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ml/endpoints", params, LIST_MAP);
    }

    /** Creates a new ML serving endpoint. */
    public Map<String, Object> createEndpoint(Map<String, Object> params) throws IOException, InterruptedException {
        return client.post("/v1/ml/endpoints", params != null ? params : Map.of(), MAP);
    }
}
