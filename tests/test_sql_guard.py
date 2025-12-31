import json
from unittest.mock import patch

from voyant.core.trino import QueryResult


def test_sql_select_allowed(client):
    result = QueryResult(
        columns=["x"],
        rows=[[1]],
        row_count=1,
        truncated=False,
        execution_time_ms=1,
        query_id="q1",
    )

    with patch("voyant_app.api.get_trino_client") as mock_client:
        mock_client.return_value.execute.return_value = result
        response = client.post(
            "/v1/sql/query",
            data=json.dumps({"sql": "select 1 as x"}),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["rows"][0][0] == 1


def test_sql_insert_blocked(client):
    with patch("voyant_app.api.get_trino_client") as mock_client:
        mock_client.return_value.execute.side_effect = ValueError("Only SELECT queries allowed")
        response = client.post(
            "/v1/sql/query",
            data=json.dumps({"sql": "insert into t values (1)"}),
            content_type="application/json",
        )

    assert response.status_code == 400
