def test_root_returns_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "DeskFlow API"
    assert body["docs"] == "/docs"


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_ready_returns_503_when_database_is_down(client, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "_database_ok", lambda db: False)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not ready"


def test_system_info_reports_version_and_db(client):
    response = client.get("/api/system")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert {"version", "git_sha", "environment"} <= body.keys()


def test_metrics_exposes_prometheus_format(client):
    client.get("/api/tickets")  # generate at least one instrumented request
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    # Business counter exists for every priority even before any ticket is created.
    assert 'deskflow_tickets_created_total{priority="urgent"}' in response.text


def test_openapi_docs_available(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/tickets" in paths and "/api/tickets/{ticket_id}" in paths
