"""The HTTP contract: status codes, shapes and error bodies, against in-memory fakes."""


def create(client, title="Rack layout", body="The backup server is in rack 4."):
    return client.post("/api/notes", json={"title": title, "body": body})


def test_create_note_returns_201_with_location_header(client):
    response = create(client)

    assert response.status_code == 201
    assert response.headers["location"] == f"/api/notes/{response.json()['id']}"


def test_create_note_strips_title_whitespace(client):
    response = create(client, title="  Trimmed  ")

    assert response.json()["title"] == "Trimmed"


def test_create_note_rejects_blank_title_with_field_error(client):
    response = create(client, title="   ")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "title" in response.json()["error"]["fields"]


def test_create_note_rejects_unknown_fields(client):
    response = client.post("/api/notes", json={"title": "x", "body": "", "pinned": True})

    assert response.status_code == 422
    assert "pinned" in response.json()["error"]["fields"]


def test_create_note_rejects_title_longer_than_200_characters(client):
    response = create(client, title="x" * 201)

    assert response.status_code == 422


def test_list_notes_returns_newest_first_with_pagination_meta(client):
    create(client, title="first")
    create(client, title="second")

    body = client.get("/api/notes?limit=1").json()

    assert [n["title"] for n in body["data"]] == ["second"]
    assert body["meta"] == {"total": 2, "limit": 1, "offset": 0}


def test_list_notes_rejects_limit_above_100(client):
    assert client.get("/api/notes?limit=101").status_code == 422


def test_get_missing_note_returns_404_error_body(client):
    response = client.get("/api/notes/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOTE_NOT_FOUND", "message": "Note 999 does not exist."}
    }


def test_patch_note_changes_only_the_fields_sent(client):
    note_id = create(client, title="old", body="keep me").json()["id"]

    updated = client.patch(f"/api/notes/{note_id}", json={"title": "new"}).json()

    assert (updated["title"], updated["body"]) == ("new", "keep me")


def test_patch_note_with_empty_payload_returns_422(client):
    note_id = create(client).json()["id"]

    assert client.patch(f"/api/notes/{note_id}", json={}).status_code == 422


def test_delete_note_returns_204_then_404(client):
    note_id = create(client).json()["id"]

    assert client.delete(f"/api/notes/{note_id}").status_code == 204
    assert client.delete(f"/api/notes/{note_id}").status_code == 404


def test_unknown_route_uses_the_error_shape(client):
    response = client.get("/api/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_responses_carry_a_request_id(client):
    response = client.get("/api/notes", headers={"X-Request-Id": "abc123"})

    assert response.headers["x-request-id"] == "abc123"


def test_ready_returns_200_when_database_ollama_and_model_are_ok(client):
    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "ollama": "ok", "model": "ok"},
    }


def test_ready_returns_503_and_names_the_missing_model(client, llm):
    llm.installed = False

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["model"] == "missing: test-model:1b"


def test_ready_returns_503_when_ollama_is_unreachable(client, llm):
    llm.reachable = False

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["ollama"] == "error: LLM_UNAVAILABLE"
