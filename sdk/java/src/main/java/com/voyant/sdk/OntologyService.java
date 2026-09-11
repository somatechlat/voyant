package com.voyant.sdk;

import com.fasterxml.jackson.core.type.TypeReference;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Ontology service — CRUD operations for Object Types, Properties, Objects,
 * Links, Interfaces, and Functions.
 *
 * <p>Usage:</p>
 * <pre>{@code
 * OntologyService ontology = client.ontology();
 * List<Map<String, Object>> types = ontology.listTypes(100);
 * Map<String, Object> type = ontology.getType("type-id");
 * Map<String, Object> created = ontology.createType("Customer", "A customer entity");
 * }</pre>
 */
public class OntologyService {

    private static final TypeReference<List<Map<String, Object>>> LIST_MAP =
            new TypeReference<>() {};
    private static final TypeReference<Map<String, Object>> MAP =
            new TypeReference<>() {};

    private final VoyantClient client;

    OntologyService(VoyantClient client) {
        this.client = client;
    }

    // ── Object Types ─────────────────────────────────────────────────────

    /** Lists all object types. */
    public List<Map<String, Object>> listTypes(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ontology/types", params, LIST_MAP);
    }

    /** Gets a single object type by ID with its properties. */
    public Map<String, Object> getType(String typeId) throws IOException, InterruptedException {
        return client.get("/v1/ontology/types/" + typeId, MAP);
    }

    /** Creates a new object type. */
    public Map<String, Object> createType(String name, String description) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("name", name);
        body.put("description", description != null ? description : "");
        return client.post("/v1/ontology/types", body, MAP);
    }

    /** Updates an existing object type. */
    public Map<String, Object> updateType(String typeId, Map<String, Object> updates) throws IOException, InterruptedException {
        return client.put("/v1/ontology/types/" + typeId, updates, MAP);
    }

    /** Deletes an object type (soft delete). */
    public void deleteType(String typeId) throws IOException, InterruptedException {
        client.delete("/v1/ontology/types/" + typeId);
    }

    // ── Object Instances ─────────────────────────────────────────────────

    /** Lists objects, optionally filtered by type. */
    public List<Map<String, Object>> listObjects(String typeID, int limit) throws IOException, InterruptedException {
        Map<String, String> params = new HashMap<>();
        params.put("limit", String.valueOf(limit));
        if (typeID != null) params.put("object_type_id", typeID);
        return client.get("/v1/ontology/objects", params, LIST_MAP);
    }

    /** Gets a single object by ID. */
    public Map<String, Object> getObject(String objectId) throws IOException, InterruptedException {
        return client.get("/v1/ontology/objects/" + objectId, MAP);
    }

    /** Creates a new object instance. */
    public Map<String, Object> createObject(String objectTypeId, Map<String, Object> properties) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("object_type_id", objectTypeId);
        body.put("properties", properties != null ? properties : Map.of());
        return client.post("/v1/ontology/objects", body, MAP);
    }

    /** Updates an existing object. */
    public Map<String, Object> updateObject(String objectId, Map<String, Object> properties, Integer version) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("properties", properties);
        if (version != null) body.put("version", version);
        return client.put("/v1/ontology/objects/" + objectId, body, MAP);
    }

    /** Deletes an object (soft delete). */
    public void deleteObject(String objectId) throws IOException, InterruptedException {
        client.delete("/v1/ontology/objects/" + objectId);
    }

    // ── Links ────────────────────────────────────────────────────────────

    /** Lists link instances. */
    public List<Map<String, Object>> listLinks(String linkTypeId, int limit) throws IOException, InterruptedException {
        Map<String, String> params = new HashMap<>();
        params.put("limit", String.valueOf(limit));
        if (linkTypeId != null) params.put("link_type_id", linkTypeId);
        return client.get("/v1/ontology/links", params, LIST_MAP);
    }

    /** Creates a new link. */
    public Map<String, Object> createLink(String linkTypeId, String sourceObjectId, String targetObjectId, Map<String, Object> properties) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("link_type_id", linkTypeId);
        body.put("source_object_id", sourceObjectId);
        body.put("target_object_id", targetObjectId);
        if (properties != null) body.put("properties", properties);
        return client.post("/v1/ontology/links", body, MAP);
    }

    /** Deletes a link (soft delete). */
    public void deleteLink(String linkId) throws IOException, InterruptedException {
        client.delete("/v1/ontology/links/" + linkId);
    }

    // ── Link Types ───────────────────────────────────────────────────────

    /** Lists all link types. */
    public List<Map<String, Object>> listLinkTypes(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ontology/link-types", params, LIST_MAP);
    }

    /** Creates a new link type. */
    public Map<String, Object> createLinkType(String name, String sourceTypeId, String targetTypeId, String cardinality) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("name", name);
        body.put("source_object_type_id", sourceTypeId);
        body.put("target_object_type_id", targetTypeId);
        body.put("cardinality", cardinality != null ? cardinality : "one_to_many");
        return client.post("/v1/ontology/link-types", body, MAP);
    }

    // ── Interfaces ───────────────────────────────────────────────────────

    /** Lists all interfaces. */
    public List<Map<String, Object>> listInterfaces(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ontology/interfaces", params, LIST_MAP);
    }

    /** Creates a new interface. */
    public Map<String, Object> createInterface(String name, String description) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("name", name);
        body.put("description", description != null ? description : "");
        return client.post("/v1/ontology/interfaces", body, MAP);
    }

    // ── Functions ────────────────────────────────────────────────────────

    /** Lists all functions. */
    public List<Map<String, Object>> listFunctions(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ontology/functions", params, LIST_MAP);
    }

    /** Creates a new function. */
    public Map<String, Object> createFunction(String name, String description, String language, String sourceCode, String entryPoint) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("name", name);
        body.put("description", description != null ? description : "");
        body.put("language", language != null ? language : "python");
        body.put("source_code", sourceCode != null ? sourceCode : "");
        body.put("entry_point", entryPoint != null ? entryPoint : "handler");
        return client.post("/v1/ontology/functions", body, MAP);
    }

    // ── Actions ──────────────────────────────────────────────────────────

    /** Lists all action types. */
    public List<Map<String, Object>> listActions(int limit) throws IOException, InterruptedException {
        Map<String, String> params = Map.of("limit", String.valueOf(limit));
        return client.get("/v1/ontology/actions", params, LIST_MAP);
    }

    /** Creates a new action type. */
    public Map<String, Object> createAction(String name, String description) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("name", name);
        body.put("description", description != null ? description : "");
        return client.post("/v1/ontology/actions", body, MAP);
    }

    // ── Traversal ────────────────────────────────────────────────────────

    /** Traverses the graph from an object following links. */
    public Map<String, Object> traverse(String objectId, int depth, List<String> linkTypes) throws IOException, InterruptedException {
        Map<String, Object> body = new HashMap<>();
        body.put("depth", depth);
        if (linkTypes != null) body.put("link_types", linkTypes);
        return client.post("/v1/ontology/objects/" + objectId + "/traverse", body, MAP);
    }
}
