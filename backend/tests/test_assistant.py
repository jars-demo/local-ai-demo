"""Retrieval-then-inference: which notes reach the prompt, and what the API reports."""

from app.assistant import build_ask_messages, clip
from app.notes import Note
from tests.conftest import BASE_TIME


def add(client, title, body):
    return client.post("/api/notes", json={"title": title, "body": body}).json()["id"]


def test_ask_sends_only_matching_notes_to_the_model(client, llm):
    rack = add(client, "Rack layout", "The backup server lives in rack four.")
    add(client, "Groceries", "Milk, eggs, coffee.")

    body = client.post("/api/ask", json={"question": "Where is the backup server?"}).json()

    assert body["retrieval"] == "search"
    assert [s["id"] for s in body["sources"]] == [rack]
    assert "Groceries" not in llm.calls[0][1]["content"]


def test_ask_reports_model_and_timings_from_the_inference(client):
    add(client, "Rack layout", "The backup server lives in rack four.")

    body = client.post("/api/ask", json={"question": "Where is the backup server?"}).json()

    assert body["answer"].startswith("From your notes")
    assert body["inference"]["model"] == "test-model:1b"
    assert body["inference"]["output_tokens"] == 18


def test_ask_falls_back_to_recent_notes_when_nothing_matches(client):
    add(client, "Groceries", "Milk, eggs, coffee.")

    body = client.post("/api/ask", json={"question": "What is the wifi password?"}).json()

    assert body["retrieval"] == "recent"
    assert body["sources"][0]["score"] is None


def test_ask_with_no_notes_answers_without_calling_the_model(client, llm):
    body = client.post("/api/ask", json={"question": "What did I write?"}).json()

    assert body["retrieval"] == "none"
    assert body["inference"] is None
    assert llm.calls == []


def test_ask_returns_503_with_error_code_when_ollama_is_down(client, llm):
    add(client, "Rack layout", "The backup server lives in rack four.")
    llm.reachable = False

    response = client.post("/api/ask", json={"question": "Where is the backup server?"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_UNAVAILABLE"


def test_ask_rejects_a_question_shorter_than_three_characters(client):
    assert client.post("/api/ask", json={"question": "hi"}).status_code == 422


def test_summary_of_a_note_uses_the_model_and_returns_its_text(client, llm):
    note_id = add(client, "Standup", "Deploy on Friday. Ask Sam about the firewall rule.")

    body = client.post(f"/api/notes/{note_id}/summary").json()

    assert body["summary"] == llm.reply
    assert "firewall rule" in llm.calls[0][1]["content"]


def test_summary_of_a_missing_note_returns_404(client):
    assert client.post("/api/notes/42/summary").status_code == 404


def test_prompt_labels_each_note_with_its_id_for_citations():
    note = Note(7, "Rack layout", "Rack four.", BASE_TIME, BASE_TIME)

    messages = build_ask_messages("Where?", [note], note_chars=100)

    assert "[#7] Rack layout" in messages[1]["content"]


def test_clip_keeps_short_text_unchanged():
    assert clip("short text", 100) == "short text"


def test_clip_cuts_long_text_on_a_word_boundary_and_marks_it():
    assert clip("alpha beta gamma", 12) == "alpha beta [...]"
