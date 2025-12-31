import json


def test_analyze_requires_table_or_source(client):
    response = client.post(
        "/v1/analyze",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 400
