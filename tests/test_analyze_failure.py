"""
Tests for Analysis Job Failure Scenarios.

This module contains tests that verify the application's behavior when
analysis jobs are initiated with invalid or missing parameters, ensuring
robust input validation and error handling.
"""

import json


def test_analyze_requires_table_or_source(client):
    """
    Verifies that the `/v1/analyze` endpoint returns a 400 Bad Request
    when neither `table` nor `source_id` is provided in the request body.
    """
    response = client.post(
        "/v1/analyze",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 400
