package voyant

import (
	"context"
	"fmt"
)

// ScraperService provides operations for the Scraper API:
// scrape tasks, templates, workflows, proxies, and scheduling.
type ScraperService struct {
	client *VoyantClient
}

// ── Scrape Tasks ─────────────────────────────────────────────────────────────

// ScrapeJob represents a web scraping job.
type ScrapeJob struct {
	ID     string `json:"id"`
	Status string `json:"status"`
}

// FetchResult represents the result of fetching a single page.
type FetchResult struct {
	URL     string `json:"url"`
	HTML    string `json:"html"`
	Status  int    `json:"status"`
	Title   string `json:"title"`
}

// StartScrape starts a new web scraping job.
func (s *ScraperService) StartScrape(ctx context.Context, urls []string, selectors, options map[string]interface{}) (*ScrapeJob, error) {
	body := map[string]interface{}{
		"urls": urls,
	}
	if selectors != nil {
		body["selectors"] = selectors
	}
	if options != nil {
		body["options"] = options
	}
	var result ScrapeJob
	err := s.client.post(ctx, "/v1/scrape/start", body, &result)
	return &result, err
}

// GetStatus returns the status of a scrape job.
func (s *ScraperService) GetStatus(ctx context.Context, jobID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, fmt.Sprintf("/v1/scrape/status/%s", jobID), nil, &result)
	return result, err
}

// GetResult returns the results and artifacts of a scrape job.
func (s *ScraperService) GetResult(ctx context.Context, jobID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, fmt.Sprintf("/v1/scrape/result/%s", jobID), nil, &result)
	return result, err
}

// CancelScrape cancels a running scrape job.
func (s *ScraperService) CancelScrape(ctx context.Context, jobID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scrape/cancel", map[string]string{"job_id": jobID}, &result)
	return result, err
}

// GetMetrics returns metrics for a scrape job.
func (s *ScraperService) GetMetrics(ctx context.Context, jobID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, fmt.Sprintf("/v1/scrape/metrics/%s", jobID), nil, &result)
	return result, err
}

// ── Fetch ────────────────────────────────────────────────────────────────────

// FetchInput holds options for fetching a single page.
type FetchInput struct {
	URL            string
	Engine         string
	WaitFor        string
	Scroll         bool
	Timeout        int
	WaitUntil      string
	SettleMs       *int
	BlockResources *bool
	CaptureJSON    bool
}

// Fetch fetches a single web page with fine-grained control.
func (s *ScraperService) Fetch(ctx context.Context, input FetchInput) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"url":     input.URL,
		"engine":  input.Engine,
		"scroll":  input.Scroll,
		"timeout": input.Timeout,
	}
	if input.Engine == "" {
		body["engine"] = "playwright"
	}
	if input.Timeout == 0 {
		body["timeout"] = 30
	}
	if input.WaitFor != "" {
		body["wait_for"] = input.WaitFor
	}
	if input.WaitUntil != "" {
		body["wait_until"] = input.WaitUntil
	}
	if input.SettleMs != nil {
		body["settle_ms"] = *input.SettleMs
	}
	if input.BlockResources != nil {
		body["block_resources"] = *input.BlockResources
	}
	if input.CaptureJSON {
		body["capture_json"] = true
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scrape/fetch", body, &result)
	return result, err
}

// ── Extract / OCR / PDF / Transcribe ─────────────────────────────────────────

// Extract extracts data from HTML using CSS/XPath selectors.
func (s *ScraperService) Extract(ctx context.Context, html string, selectors map[string]interface{}) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"html":      html,
		"selectors": selectors,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scrape/extract", body, &result)
	return result, err
}

// OCR runs optical character recognition on an image.
func (s *ScraperService) OCR(ctx context.Context, imageURL, language string) (map[string]interface{}, error) {
	if language == "" {
		language = "spa+eng"
	}
	body := map[string]interface{}{
		"image_url": imageURL,
		"language":  language,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scrape/ocr", body, &result)
	return result, err
}

// ParsePDF parses a PDF document and extracts content.
func (s *ScraperService) ParsePDF(ctx context.Context, pdfURL string, extractTables bool) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"pdf_url":        pdfURL,
		"extract_tables": extractTables,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scrape/parse_pdf", body, &result)
	return result, err
}

// Transcribe transcribes audio/media files.
func (s *ScraperService) Transcribe(ctx context.Context, mediaURL, language string) (map[string]interface{}, error) {
	if language == "" {
		language = "es"
	}
	body := map[string]interface{}{
		"media_url": mediaURL,
		"language":  language,
	}
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scrape/transcribe", body, &result)
	return result, err
}

// ── Templates & Workflows ────────────────────────────────────────────────────

// ListTasks returns scraper tasks (v2).
func (s *ScraperService) ListTasks(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/scraper/v2/tasks", params, &result)
	return result, err
}

// CreateTask creates a new scraper task (v2).
func (s *ScraperService) CreateTask(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scraper/v2/tasks", params, &result)
	return result, err
}

// ListTemplates returns scraper templates (v2).
func (s *ScraperService) ListTemplates(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/scraper/v2/templates", params, &result)
	return result, err
}

// CreateTemplate creates a new scraper template (v2).
func (s *ScraperService) CreateTemplate(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scraper/v2/templates", params, &result)
	return result, err
}

// ListWorkflows returns scraper workflows (v2).
func (s *ScraperService) ListWorkflows(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/scraper/v2/workflows", params, &result)
	return result, err
}

// ListProxies returns available proxy configurations.
func (s *ScraperService) ListProxies(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/scraper/v2/proxies", params, &result)
	return result, err
}

// ListSchedules returns scraper schedules.
func (s *ScraperService) ListSchedules(ctx context.Context, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/scraper/v2/schedules", params, &result)
	return result, err
}

// ListRuns returns scraper run history.
func (s *ScraperService) ListRuns(ctx context.Context, taskID *string, limit *int) ([]map[string]interface{}, error) {
	params := map[string]string{}
	if taskID != nil {
		params["task_id"] = *taskID
	}
	if limit != nil {
		params["limit"] = fmt.Sprintf("%d", *limit)
	}
	var result []map[string]interface{}
	err := s.client.get(ctx, "/v1/scraper/v2/runs", params, &result)
	return result, err
}

// GenerateFingerprint generates a browser fingerprint.
func (s *ScraperService) GenerateFingerprint(ctx context.Context) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.post(ctx, "/v1/scraper/v2/fingerprints/generate", nil, &result)
	return result, err
}

// Health checks the scraper service health.
func (s *ScraperService) Health(ctx context.Context) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := s.client.get(ctx, "/v1/scrape/health", nil, &result)
	return result, err
}
