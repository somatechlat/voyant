# Voyant Project - Code & Architecture Violations

This document tracks identified violations of VIBE coding rules, architectural principles, and general best practices. Each entry includes a description of the issue, its status, and the files it affects.

---

### **1. Critical Test Suite Failures**

-   **ID:** V-001
-   **Status:** **Unresolved**
-   **Severity:** Critical
-   **Description:** The `pytest` suite fails during test collection, preventing any tests from running. This indicates fundamental errors in the application code or test setup, making it impossible to validate functionality automatically. The primary cause appears to be `ModuleNotFoundError` related to `temporalio` and a `TypeError` in `analysis_activities.py`.
-   **Affected Files:**
    -   `tests/activities/test_analysis_activities.py`
    -   `tests/activities/test_generation_activities.py`
    -   `tests/integration/test_operational_workflows.py`
    -   `tests/integration/test_staging_flow.py`
    -   `tests/test_fix_data_quality.py`
-   **Personas Violated:** PhD QA Engineer, PhD Developer.
-   **Suggested Resolution:** Debug the import errors and TypeErrors to allow the test suite to collect and run. This is the highest priority for stabilizing the project.

---

### **2. Extremely Low Test Coverage**

-   **ID:** V-002
-   **Status:** **Unresolved**
-   **Severity:** Critical
-   **Description:** Code test coverage is approximately **13%**. This means 87% of the codebase is not executed during testing and is completely unvalidated. This level of coverage is far below any acceptable standard for a reliable application.
-   **Affected Files:**
    -   Virtually all files in `voyant/`
-   **Personas Violated:** PhD QA Engineer.
-   **Suggested Resolution:** Implement a comprehensive testing strategy and write unit, integration, and E2E tests to significantly increase coverage, focusing on critical modules in `voyant/core/` and `voyant_app/` first.

---

### **3. Severe Code Quality Issues (Linting & Type Checking)**

-   **ID:** V-003
-   **Status:** **Partially Resolved** (Formatting fixed by `black`)
-   **Severity:** Major
-   **Description:** The codebase contains a very high number of errors identified by `ruff` (433) and `pyright` (313). While formatting was corrected, severe issues remain, including:
    -   Use of bare `except` clauses.
    -   Undefined names (e.g., `List` in `voyant/ingestion/airbyte_utils.py`), which will cause runtime crashes.
    -   Widespread type mismatches and improper use of `None`.
    -   The `lint` command in the `Makefile` is a non-functional placeholder, indicating a lack of quality control in the development process.
-   **Affected Files:**
    -   Most Python files throughout the project.
-   **Personas Violated:** PhD Developer, ISO Documenter, PhD QA Engineer.
-   **Suggested Resolution:**
    1.  Fix the `Makefile` to include a functional `lint` and `type-check` command.
    2.  Systematically fix all critical and major errors reported by `ruff` and `pyright`.

---

### **4. Insecure Default Settings**

-   **ID:** V-005
-   **Status:** **Partially Resolved** (Documentation added)
-   **Severity:** Major
-   **Description:** The main Django settings file (`voyant_project/settings.py`) contains insecure default values for development that are dangerous if used in production. This includes a default `SECRET_KEY`, `DEBUG = True` logic, and permissive `ALLOWED_HOSTS` and `CORS` settings.
-   **Affected Files:**
    -   `voyant_project/settings.py`
-   **Personas Violated:** Security Auditor.
-   **Suggested Resolution:** While documentation has been added to warn developers, the principle of "secure by default" would suggest removing hardcoded insecure keys entirely, forcing them to be set via environment variables in all environments. This is a longer-term architectural improvement.

---

### **5. Redundant OCR Processor Implementations**

-   **ID:** V-006
-   **Status:** **Unresolved**
-   **Severity:** Major
-   **Description:** There are two separate modules providing OCR processing functionality: `voyant/scraper/media/ocr.py` and `voyant/scraper/parsing/ocr_processor.py`. Both define a class named `OCRProcessor` and aim to extract text from images/PDFs. This redundancy creates architectural confusion, duplicates logic, and makes maintenance harder. `voyant/scraper/media/ocr.py` appears to be a higher-level orchestrator, while `voyant/scraper/parsing/ocr_processor.py` is a Tesseract-specific implementation.
-   **Affected Files:**
    -   `voyant/scraper/media/ocr.py`
    -   `voyant/scraper/parsing/ocr_processor.py`
-   **Suggested Resolution:** Refactor the OCR functionality to consolidate into a single, well-defined module. The `voyant/scraper/media/ocr.py` could serve as the primary abstraction, delegating to internal, engine-specific implementations (possibly moving the Tesseract-specific logic from `voyant/scraper/parsing/ocr_processor.py` into `voyant/scraper/media/ocr.py`'s private methods or a dedicated sub-module).

---

### **6. Test Failure: Incorrect Airbyte Client Method**

-   **ID:** V-007
-   **Status:** **Unresolved**
-   **Severity:** Critical
-   **Description:** The test `tests/test_airbyte_health.py` attempts to call `client.health()` on an `AirbyteClient` instance, but the `AirbyteClient` class defines an `is_healthy()` method instead. This causes a test failure.
-   **Affected Files:**
    -   `tests/test_airbyte_health.py`
-   **Suggested Resolution:** Correct the method call in `tests/test_airbyte_health.py` from `client.health()` to `client.is_healthy()`.

---

### **7. Empty Test File**

-   **ID:** V-008
-   **Status:** **Unresolved**
-   **Severity:** Minor
-   **Description:** The file `tests/test_bundle_partial_failure.py` is empty, despite being a designated test file. This indicates incomplete test coverage or an abandoned test module.
-   **Affected Files:**
    -   `tests/test_bundle_partial_failure.py`
-   **Suggested Resolution:** Populate the file with relevant tests for partial bundle failure scenarios, or remove the file if it's no longer needed.

---

### **8. Empty Test File**

-   **ID:** V-009
-   **Status:** **Unresolved**
-   **Severity:** Minor
-   **Description:** The file `tests/test_chart_heuristics.py` is empty, despite being a designated test file. This indicates incomplete test coverage or an abandoned test module.
-   **Affected Files:**
    -   `tests/test_chart_heuristics.py`
-   **Suggested Resolution:** Populate the file with relevant tests for chart heuristic scenarios, or remove the file if it's no longer needed.

---

### **9. Empty Test File**

-   **ID:** V-010
-   **Status:** **Unresolved**
-   **Severity:** Minor
-   **Description:** The file `tests/test_ckan_search.py` is empty, despite being a designated test file. This indicates incomplete test coverage or an abandoned test module.
-   **Affected Files:**
    -   `tests/test_ckan_search.py`
-   **Suggested Resolution:** Populate the file with relevant tests for CKAN search integration scenarios, or remove the file if it's no longer needed.

---

### **10. Empty Test File**

-   **ID:** V-011
-   **Status:** **Unresolved**
-   **Severity:** Minor
-   **Description:** The file `tests/test_config_reload.py` is empty, despite being a designated test file. This indicates incomplete test coverage or an abandoned test module.
-   **Affected Files:**
    -   `tests/test_config_reload.py`
-   **Suggested Resolution:** Populate the file with relevant tests for configuration reloading scenarios, or remove the file if it's no longer needed.

---

### **11. Empty Test File**

-   **ID:** V-012
-   **Status:** **Unresolved**
-   **Severity:** Minor
-   **Description:** The file `tests/test_dashboard_and_charts.py` is empty, despite being a designated test file. This indicates incomplete test coverage or an abandoned test module.
-   **Affected Files:**
    -   `tests/test_dashboard_and_charts.py`
-   **Suggested Resolution:** Populate the file with relevant tests for dashboard and chart generation and display, or remove the file if it's no longer needed.

---

### **12. Empty Test File**

-   **ID:** V-013
-   **Status:** **Unresolved**
-   **Severity:** Minor
-   **Description:** The file `tests/test_e2e_smoke.py` is empty, despite being a designated test file. This indicates incomplete test coverage or an abandoned test module.
-   **Affected Files:**
    -   `tests/test_e2e_smoke.py`
-   **Suggested Resolution:** Populate the file with relevant tests for end-to-end smoke test scenarios, or remove the file if it's no longer needed.

---

### **13. Empty Test File**

-   **ID:** V-014
-   **Status:** **Unresolved**
-   **Severity:** Minor
-   **Description:** The file `tests/test_health.py` is empty, despite being a designated test file. This indicates incomplete test coverage or an abandoned test module.
-   **Affected Files:**
    -   `tests/test_health.py`
-   **Suggested Resolution:** Populate the file with relevant tests for basic health checks, or remove the file if it's no longer needed (given the more comprehensive `test_health_endpoints.py`).