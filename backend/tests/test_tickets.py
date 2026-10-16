import pytest

# ---------- POST /api/tickets ----------


def test_create_ticket_returns_201_with_defaults(client, ticket_payload):
    response = client.post("/api/tickets", json=ticket_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == ticket_payload["title"]
    assert body["status"] == "open"
    assert body["assignee"] is None
    assert body["created_at"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "ab"),  # too short
        ("requester_email", "not-an-email"),
        ("priority", "critical"),  # not an allowed enum value
        ("category", "hardware"),
    ],
)
def test_create_ticket_rejects_invalid_input(client, ticket_payload, field, value):
    response = client.post("/api/tickets", json={**ticket_payload, field: value})
    assert response.status_code == 422


def test_create_ticket_requires_title_and_email(client):
    response = client.post("/api/tickets", json={"description": "missing fields"})
    assert response.status_code == 422
    missing = {err["loc"][-1] for err in response.json()["detail"]}
    assert {"title", "requester_email"} <= missing


# ---------- GET /api/tickets ----------


def test_list_tickets_empty(client):
    response = client.get("/api/tickets")
    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}


def test_list_tickets_newest_first(client, create_ticket):
    first = create_ticket(title="First ticket")
    second = create_ticket(title="Second ticket")
    items = client.get("/api/tickets").json()["items"]
    assert [t["id"] for t in items] == [second["id"], first["id"]]


def test_list_tickets_filters_by_status_and_priority(client, create_ticket):
    create_ticket(priority="urgent")
    create_ticket(priority="low", status="resolved")
    create_ticket(priority="urgent", status="resolved")

    urgent = client.get("/api/tickets", params={"priority": "urgent"}).json()
    assert urgent["total"] == 2

    resolved_urgent = client.get(
        "/api/tickets", params={"priority": "urgent", "status": "resolved"}
    ).json()
    assert resolved_urgent["total"] == 1


def test_list_tickets_unassigned_filter(client, create_ticket):
    create_ticket(assignee="Neha")
    unowned = create_ticket()
    body = client.get("/api/tickets", params={"unassigned": "true"}).json()
    assert [t["id"] for t in body["items"]] == [unowned["id"]]


def test_list_tickets_search(client, create_ticket):
    create_ticket(title="Invoice charged twice", requester_email="finance@acme.io")
    create_ticket(title="Dark mode request")
    assert client.get("/api/tickets", params={"q": "invoice"}).json()["total"] == 1
    assert client.get("/api/tickets", params={"q": "acme"}).json()["total"] == 1


def test_list_tickets_rejects_unknown_status(client):
    assert client.get("/api/tickets", params={"status": "pending"}).status_code == 422


# ---------- GET /api/tickets/{id} ----------


def test_get_ticket_by_id(client, create_ticket):
    created = create_ticket()
    response = client.get(f"/api/tickets/{created['id']}")
    assert response.status_code == 200
    assert response.json()["requester_email"] == "priya@example.com"


def test_get_missing_ticket_returns_404(client):
    response = client.get("/api/tickets/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# ---------- PUT /api/tickets/{id} ----------


def test_update_ticket_status_and_assignee(client, create_ticket):
    created = create_ticket()
    response = client.put(
        f"/api/tickets/{created['id']}", json={"status": "in_progress", "assignee": "Aadit"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["assignee"] == "Aadit"
    assert body["title"] == created["title"]  # untouched fields are preserved


def test_update_can_unassign(client, create_ticket):
    created = create_ticket(assignee="Aadit")
    response = client.put(f"/api/tickets/{created['id']}", json={"assignee": None})
    assert response.json()["assignee"] is None


def test_update_missing_ticket_returns_404(client):
    assert client.put("/api/tickets/9999", json={"status": "closed"}).status_code == 404


def test_update_rejects_invalid_status(client, create_ticket):
    created = create_ticket()
    response = client.put(f"/api/tickets/{created['id']}", json={"status": "done"})
    assert response.status_code == 422


# ---------- DELETE /api/tickets/{id} ----------


def test_delete_ticket(client, create_ticket):
    created = create_ticket()
    assert client.delete(f"/api/tickets/{created['id']}").status_code == 204
    assert client.get(f"/api/tickets/{created['id']}").status_code == 404


def test_delete_missing_ticket_returns_404(client):
    assert client.delete("/api/tickets/9999").status_code == 404


# ---------- GET /api/tickets/stats ----------


def test_stats_on_empty_database(client):
    body = client.get("/api/tickets/stats").json()
    assert body["total"] == 0
    assert body["resolution_rate"] == 0.0
    assert body["by_status"] == {"open": 0, "in_progress": 0, "resolved": 0, "closed": 0}


def test_stats_aggregates_tickets(client, create_ticket):
    create_ticket(priority="urgent")  # open + urgent + unassigned
    create_ticket(priority="urgent", status="in_progress", assignee="Sam")
    create_ticket(priority="low", status="resolved")
    create_ticket(priority="urgent", status="closed")  # closed urgent doesn't count

    body = client.get("/api/tickets/stats").json()
    assert body["total"] == 4
    assert body["by_priority"]["urgent"] == 3
    assert body["by_status"]["resolved"] == 1
    assert body["open_urgent"] == 2
    assert body["unassigned"] == 1
    assert body["resolution_rate"] == 50.0


# ---------- GET /api/activity ----------


def test_activity_feed_records_lifecycle(client, create_ticket):
    created = create_ticket(title="Lifecycle ticket")
    client.put(f"/api/tickets/{created['id']}", json={"status": "resolved"})
    client.delete(f"/api/tickets/{created['id']}")

    feed = client.get("/api/activity").json()
    assert [entry["action"] for entry in feed] == ["deleted", "updated", "created"]
    assert feed[1]["detail"] == "status → resolved"
    assert all(entry["ticket_title"] == "Lifecycle ticket" for entry in feed)


def test_noop_update_does_not_log_activity(client, create_ticket):
    created = create_ticket(priority="high")
    client.put(f"/api/tickets/{created['id']}", json={"priority": "high"})
    assert len(client.get("/api/activity").json()) == 1
