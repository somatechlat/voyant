// Package voyant provides the official Go SDK for the Voyant Data Intelligence API.
//
// Usage:
//
//	client := voyant.NewClient("http://localhost:8000", "your-api-key")
//	types, err := client.Ontology.ListTypes(ctx, nil)
//	models, err := client.ML.ListModels(ctx, nil)
//	tasks, err := client.Scraper.ListTasks(ctx, nil)
package voyant

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const (
	defaultBaseURL = "http://localhost:8000"
	defaultTimeout = 60 * time.Second
	userAgent      = "voyant-go-sdk/1.0.0"
)

// APIError represents an error returned by the Voyant API.
type APIError struct {
	StatusCode int         `json:"status_code"`
	Message    string      `json:"message"`
	ErrorCode  string      `json:"error_code,omitempty"`
	Detail     interface{} `json:"detail,omitempty"`
}

func (e *APIError) Error() string {
	return fmt.Sprintf("voyant API error %d: %s", e.StatusCode, e.Message)
}

// ClientConfig holds configuration for the VoyantClient.
type ClientConfig struct {
	BaseURL  string
	APIKey   string
	Timeout  time.Duration
	TenantID string
}

// VoyantClient is the main entry point for interacting with the Voyant API.
type VoyantClient struct {
	httpClient *http.Client
	baseURL    string
	apiKey     string
	tenantID   string

	// Service namespaces
	Ontology *OntologyService
	ML       *MLService
	Scraper  *ScraperService
}

// NewClient creates a new VoyantClient with the given base URL and API key.
func NewClient(baseURL, apiKey string) *VoyantClient {
	return NewClientWithConfig(ClientConfig{
		BaseURL: baseURL,
		APIKey:  apiKey,
	})
}

// NewClientWithConfig creates a new VoyantClient with full configuration.
func NewClientWithConfig(cfg ClientConfig) *VoyantClient {
	if cfg.BaseURL == "" {
		cfg.BaseURL = defaultBaseURL
	}
	if cfg.Timeout == 0 {
		cfg.Timeout = defaultTimeout
	}

	c := &VoyantClient{
		httpClient: &http.Client{Timeout: cfg.Timeout},
		baseURL:    strings.TrimRight(cfg.BaseURL, "/"),
		apiKey:     cfg.APIKey,
		tenantID:   cfg.TenantID,
	}

	c.Ontology = &OntologyService{client: c}
	c.ML = &MLService{client: c}
	c.Scraper = &ScraperService{client: c}

	return c
}

// Health checks the API health endpoint.
func (c *VoyantClient) Health(ctx context.Context) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.get(ctx, "/health", nil, &result)
	return result, err
}

// ── Internal HTTP helpers ────────────────────────────────────────────────────

func (c *VoyantClient) headers() http.Header {
	h := http.Header{}
	h.Set("Content-Type", "application/json")
	h.Set("User-Agent", userAgent)
	if c.apiKey != "" {
		h.Set("Authorization", "Bearer "+c.apiKey)
	}
	if c.tenantID != "" {
		h.Set("X-Tenant-ID", c.tenantID)
	}
	return h
}

func (c *VoyantClient) do(ctx context.Context, method, path string, body interface{}, result interface{}) error {
	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal request body: %w", err)
		}
		bodyReader = bytes.NewReader(data)
	}

	fullURL := c.baseURL + path
	req, err := http.NewRequestWithContext(ctx, method, fullURL, bodyReader)
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header = c.headers()

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		var apiErr APIError
		apiErr.StatusCode = resp.StatusCode
		respData, _ := io.ReadAll(resp.Body)
		if err := json.Unmarshal(respData, &apiErr); err != nil {
			apiErr.Message = string(respData)
		}
		return &apiErr
	}

	if resp.StatusCode == http.StatusNoContent {
		return nil
	}

	if result != nil {
		if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
			return fmt.Errorf("decode response: %w", err)
		}
	}
	return nil
}

func (c *VoyantClient) get(ctx context.Context, path string, params map[string]string, result interface{}) error {
	if len(params) > 0 {
		q := url.Values{}
		for k, v := range params {
			q.Set(k, v)
		}
		path = path + "?" + q.Encode()
	}
	return c.do(ctx, http.MethodGet, path, nil, result)
}

func (c *VoyantClient) post(ctx context.Context, path string, body, result interface{}) error {
	return c.do(ctx, http.MethodPost, path, body, result)
}

func (c *VoyantClient) put(ctx context.Context, path string, body, result interface{}) error {
	return c.do(ctx, http.MethodPut, path, body, result)
}

func (c *VoyantClient) delete(ctx context.Context, path string) error {
	return c.do(ctx, http.MethodDelete, path, nil, nil)
}
