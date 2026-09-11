package voyant

import (
	"context"
	"fmt"
)

// MLService provides operations for the ML Platform API:
// models, experiments, runs, agents, and endpoints.
type MLService struct {
	client *VoyantClient
}

// ── Models ───────────────────────────────────────────────────────────────────

// MLModel represents a registered ML model.
type MLModel struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Version     int    `json:"version"`
	TenantID    string `json:"tenant_id"`
	CreatedAt   string `json:"created_at"`
}

// ModelVersion represents a specific version of an ML model.
type ModelVersion struct {
	ID        string `json:"id"`
	ModelID   string `json:"model_id"`
	Version   string `json:"version"`
	Stage     string `json:"stage"`
	CreatedAt string `json:"created_at"`
}

// ListModels returns all registered ML models.
func (s *MLService) ListModels(ctx context.Context, limit *int) ([]MLModel, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []MLModel
	err := s.client.get(ctx, "/v1/ml/models", params, &result)
	return result, err
}

// GetModel returns a single ML model by ID.
func (s *MLService) GetModel(ctx context.Context, modelID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, fmt.Sprintf("/v1/ml/models/%s", modelID), nil, &result)
	return result, err
}

// CreateModel creates a new ML model registry entry.
func (s *MLService) CreateModel(ctx context.Context, name, description string) (*MLModel, error) {
	body := map[string]interface{}{
		"name":        name,
		"description": description,
	}
	var result MLModel
	err := s.client.post(ctx, "/v1/ml/models", body, &result)
	return &result, err
}

// CreateModelVersion creates a new version for an existing model.
func (s *MLService) CreateModelVersion(ctx context.Context, modelID string, params map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.post(ctx, fmt.Sprintf("/v1/ml/models/%s/versions", modelID), params, &result)
	return result, err
}

// SetModelStage promotes a model version to a specific stage (staging, production, archived).
func (s *MLService) SetModelStage(ctx context.Context, versionID, stage string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.put(ctx, fmt.Sprintf("/v1/ml/model-versions/%s/stage", versionID), map[string]string{"stage": stage}, &result)
	return result, err
}

// ── Experiments ──────────────────────────────────────────────────────────────

// Experiment represents an ML experiment.
type Experiment struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	TenantID  string `json:"tenant_id"`
	CreatedAt string `json:"created_at"`
}

// Run represents a run within an experiment.
type Run struct {
	ID           string                 `json:"id"`
	ExperimentID string                 `json:"experiment_id"`
	Status       string                 `json:"status"`
	Parameters   map[string]interface{} `json:"parameters"`
	Metrics      map[string]interface{} `json:"metrics"`
	TenantID     string                 `json:"tenant_id"`
	CreatedAt    string                 `json:"created_at"`
}

// ListExperiments returns all experiments.
func (s *MLService) ListExperiments(ctx context.Context, limit *int) ([]Experiment, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []Experiment
	err := s.client.get(ctx, "/v1/ml/experiments", params, &result)
	return result, err
}

// GetExperiment returns a single experiment by ID.
func (s *MLService) GetExperiment(ctx context.Context, experimentID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, fmt.Sprintf("/v1/ml/experiments/%s", experimentID), nil, &result)
	return result, err
}

// CreateExperiment creates a new experiment.
func (s *MLService) CreateExperiment(ctx context.Context, name string, params map[string]interface{}) (*Experiment, error) {
	body := map[string]interface{}{
		"name": name,
	}
	for k, v := range params {
		body[k] = v
	}
	var result Experiment
	err := s.client.post(ctx, "/v1/ml/experiments", body, &result)
	return &result, err
}

// CreateRun creates a new run within an experiment.
func (s *MLService) CreateRun(ctx context.Context, experimentID string, params map[string]interface{}) (*Run, error) {
	var result Run
	err := s.client.post(ctx, fmt.Sprintf("/v1/ml/experiments/%s/runs", experimentID), params, &result)
	return &result, err
}

// LogMetrics logs metrics for a specific run.
func (s *MLService) LogMetrics(ctx context.Context, runID string, metrics map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.put(ctx, fmt.Sprintf("/v1/ml/runs/%s/metrics", runID), metrics, &result)
	return result, err
}

// ── Agents ───────────────────────────────────────────────────────────────────

// Agent represents an ML agent.
type Agent struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	TenantID  string `json:"tenant_id"`
	CreatedAt string `json:"created_at"`
}

// ListAgents returns all ML agents.
func (s *MLService) ListAgents(ctx context.Context, limit *int) ([]Agent, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []Agent
	err := s.client.get(ctx, "/v1/ml/agents", params, &result)
	return result, err
}

// GetAgent returns a single agent by ID.
func (s *MLService) GetAgent(ctx context.Context, agentID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, fmt.Sprintf("/v1/ml/agents/%s", agentID), nil, &result)
	return result, err
}

// CreateAgent creates a new ML agent.
func (s *MLService) CreateAgent(ctx context.Context, name string, params map[string]interface{}) (*Agent, error) {
	body := map[string]interface{}{
		"name": name,
	}
	for k, v := range params {
		body[k] = v
	}
	var result Agent
	err := s.client.post(ctx, "/v1/ml/agents", body, &result)
	return &result, err
}

// UpdateAgent updates an existing ML agent.
func (s *MLService) UpdateAgent(ctx context.Context, agentID string, updates map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.put(ctx, fmt.Sprintf("/v1/ml/agents/%s", agentID), updates, &result)
	return result, err
}

// DeleteAgent deletes an ML agent.
func (s *MLService) DeleteAgent(ctx context.Context, agentID string) error {
	return s.client.delete(ctx, fmt.Sprintf("/v1/ml/agents/%s", agentID))
}

// ── Endpoints ────────────────────────────────────────────────────────────────

// ListEndpoints returns all ML serving endpoints.
func (s *MLService) ListEndpoints(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/ml/endpoints", params, &result)
	return result, err
}

// CreateEndpoint creates a new ML serving endpoint.
func (s *MLService) CreateEndpoint(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/ml/endpoints", params, &result)
	return result, err
}
