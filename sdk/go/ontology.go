package voyant

import (
	"context"
	"fmt"
)

// OntologyService provides CRUD operations for the Ontology API:
// Object Types, Properties, Objects, Links, Interfaces, and Functions.
type OntologyService struct {
	client *VoyantClient
}

// ── Object Types ─────────────────────────────────────────────────────────────

// ObjectType represents an ontology object type (schema definition).
type ObjectType struct {
	ID              string `json:"id"`
	Name            string `json:"name"`
	Description     string `json:"description"`
	Version         int    `json:"version"`
	PropertyCount   int    `json:"property_count"`
	InstanceCount   int    `json:"instance_count"`
	TenantID        string `json:"tenant_id"`
	CreatedAt       string `json:"created_at"`
}

// CreateObjectTypeInput holds parameters for creating an object type.
type CreateObjectTypeInput struct {
	Name        string                   `json:"name"`
	Description string                   `json:"description,omitempty"`
	Properties  []map[string]interface{} `json:"properties,omitempty"`
}

// ListTypes returns all object types for the current tenant.
func (s *OntologyService) ListTypes(ctx context.Context, limit *int) ([]ObjectType, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []ObjectType
	err := s.client.get(ctx, "/v1/ontology/types", params, &result)
	return result, err
}

// GetType returns a single object type by ID.
func (s *OntologyService) GetType(ctx context.Context, typeID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, fmt.Sprintf("/v1/ontology/types/%s", typeID), nil, &result)
	return result, err
}

// CreateType creates a new object type.
func (s *OntologyService) CreateType(ctx context.Context, input CreateObjectTypeInput) (*ObjectType, error) {
	var result ObjectType
	err := s.client.post(ctx, "/v1/ontology/types", input, &result)
	return &result, err
}

// UpdateType updates an existing object type.
func (s *OntologyService) UpdateType(ctx context.Context, typeID string, updates map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.put(ctx, fmt.Sprintf("/v1/ontology/types/%s", typeID), updates, &result)
	return result, err
}

// DeleteType soft-deletes an object type.
func (s *OntologyService) DeleteType(ctx context.Context, typeID string) error {
	return s.client.delete(ctx, fmt.Sprintf("/v1/ontology/types/%s", typeID))
}

// ── Object Instances ─────────────────────────────────────────────────────────

// Object represents an instance of an object type.
type Object struct {
	ID           string                 `json:"id"`
	ObjectType   string                 `json:"object_type"`
	Properties   map[string]interface{} `json:"properties"`
	Version      int                    `json:"version"`
	TenantID     string                 `json:"tenant_id"`
	CreatedAt    string                 `json:"created_at"`
}

// ListObjects returns objects, optionally filtered by type.
func (s *OntologyService) ListObjects(ctx context.Context, typeID *string, limit *int) ([]Object, error) {
	params := map[string]string{}
	if typeID != nil {
		params["object_type_id"] = *typeID
	}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []Object
	err := s.client.get(ctx, "/v1/ontology/objects", params, &result)
	return result, err
}

// GetObject returns a single object by ID.
func (s *OntologyService) GetObject(ctx context.Context, objectID string) (*Object, error) {
	var result Object
	err := s.client.get(ctx, fmt.Sprintf("/v1/ontology/objects/%s", objectID), nil, &result)
	return &result, err
}

// CreateObject creates a new object instance.
func (s *OntologyService) CreateObject(ctx context.Context, objectTypeID string, properties map[string]interface{}) (*Object, error) {
	body := map[string]interface{}{
		"object_type_id": objectTypeID,
		"properties":     properties,
	}
	var result Object
	err := s.client.post(ctx, "/v1/ontology/objects", body, &result)
	return &result, err
}

// UpdateObject updates an existing object.
func (s *OntologyService) UpdateObject(ctx context.Context, objectID string, properties map[string]interface{}, version *int) (*Object, error) {
	body := map[string]interface{}{
		"properties": properties,
	}
	if version != nil {
		body["version"] = *version
	}
	var result Object
	err := s.client.put(ctx, fmt.Sprintf("/v1/ontology/objects/%s", objectID), body, &result)
	return &result, err
}

// DeleteObject soft-deletes an object.
func (s *OntologyService) DeleteObject(ctx context.Context, objectID string) error {
	return s.client.delete(ctx, fmt.Sprintf("/v1/ontology/objects/%s", objectID))
}

// BatchCreate creates multiple objects at once.
func (s *OntologyService) BatchCreate(ctx context.Context, objectTypeID string, items []map[string]interface{}) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"object_type_id": objectTypeID,
		"items":          items,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/ontology/objects/batch", body, &result)
	return result, err
}

// ── Links ────────────────────────────────────────────────────────────────────

// Link represents a relationship between two objects.
type Link struct {
	ID           string                 `json:"id"`
	LinkType     string                 `json:"link_type"`
	SourceObject string                 `json:"source_object"`
	TargetObject string                 `json:"target_object"`
	Properties   map[string]interface{} `json:"properties"`
	TenantID     string                 `json:"tenant_id"`
}

// ListLinks returns link instances.
func (s *OntologyService) ListLinks(ctx context.Context, linkTypeID *string, limit *int) ([]Link, error) {
	params := map[string]string{}
	if linkTypeID != nil {
		params["link_type_id"] = *linkTypeID
	}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []Link
	err := s.client.get(ctx, "/v1/ontology/links", params, &result)
	return result, err
}

// CreateLink creates a new link instance.
func (s *OntologyService) CreateLink(ctx context.Context, linkTypeID, sourceObjectID, targetObjectID string, properties map[string]interface{}) (*Link, error) {
	body := map[string]interface{}{
		"link_type_id":     linkTypeID,
		"source_object_id": sourceObjectID,
		"target_object_id": targetObjectID,
	}
	if properties != nil {
		body["properties"] = properties
	}
	var result Link
	err := s.client.post(ctx, "/v1/ontology/links", body, &result)
	return &result, err
}

// DeleteLink soft-deletes a link.
func (s *OntologyService) DeleteLink(ctx context.Context, linkID string) error {
	return s.client.delete(ctx, fmt.Sprintf("/v1/ontology/links/%s", linkID))
}

// ── Link Types ───────────────────────────────────────────────────────────────

// ListLinkTypes returns all link types.
func (s *OntologyService) ListLinkTypes(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/ontology/link-types", params, &result)
	return result, err
}

// CreateLinkType creates a new link type.
func (s *OntologyService) CreateLinkType(ctx context.Context, name, sourceTypeID, targetTypeID, cardinality string) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"name":                 name,
		"source_object_type_id": sourceTypeID,
		"target_object_type_id": targetTypeID,
		"cardinality":          cardinality,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/ontology/link-types", body, &result)
	return result, err
}

// ── Interfaces ───────────────────────────────────────────────────────────────

// ListInterfaces returns all interfaces.
func (s *OntologyService) ListInterfaces(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/ontology/interfaces", params, &result)
	return result, err
}

// CreateInterface creates a new interface.
func (s *OntologyService) CreateInterface(ctx context.Context, name, description string) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"name":        name,
		"description": description,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/ontology/interfaces", body, &result)
	return result, err
}

// ── Functions ────────────────────────────────────────────────────────────────

// ListFunctions returns all functions.
func (s *OntologyService) ListFunctions(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/ontology/functions", params, &result)
	return result, err
}

// CreateFunction creates a new function.
func (s *OntologyService) CreateFunction(ctx context.Context, name, description, language, sourceCode, entryPoint string) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"name":         name,
		"description":  description,
		"language":     language,
		"source_code":  sourceCode,
		"entry_point":  entryPoint,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/ontology/functions", body, &result)
	return result, err
}

// ── Actions ──────────────────────────────────────────────────────────────────

// ListActions returns all action types.
func (s *OntologyService) ListActions(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/ontology/actions", params, &result)
	return result, err
}

// CreateAction creates a new action type.
func (s *OntologyService) CreateAction(ctx context.Context, name, description string) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"name":        name,
		"description": description,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/ontology/actions", body, &result)
	return result, err
}

// ── Traversal ────────────────────────────────────────────────────────────────

// Traverse traverses the graph from an object, following links up to a given depth.
func (s *OntologyService) Traverse(ctx context.Context, objectID string, depth int, linkTypes []string) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"depth": depth,
	}
	if linkTypes != nil {
		body["link_types"] = linkTypes
	}
	var result map[string]interface{}
	err := s.client.post(ctx, fmt.Sprintf("/v1/ontology/objects/%s/traverse", objectID), body, &result)
	return result, err
}
