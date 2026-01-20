from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture()
def client(tmp_path: Path):
    original_path = server.principles_service.base_path
    server.principles_service.base_path = tmp_path
    server.principles_service.base_path.mkdir(parents=True, exist_ok=True)

    # Seed one default principle
    (tmp_path / "agile.md").write_text(
        "# Agile Meeting Principles\n\n1. **수평적 의사결정**\n", encoding="utf-8"
    )

    yield TestClient(server.app)
    server.principles_service.base_path = original_path


def test_list_principles(client: TestClient):
    response = client.get("/api/v1/principles")
    assert response.status_code == 200
    payload = response.json()
    assert "principles" in payload
    assert any(item["id"] == "agile" for item in payload["principles"])


def test_create_update_delete_principle(client: TestClient, tmp_path: Path):
    create_payload = {
        "name": "Design Sprint Principles",
        "content": "1. **Timebox**\n   Keep it tight.",
    }
    create_response = client.post("/api/v1/principles", json=create_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"]

    created_file = tmp_path / f"{created['id']}.md"
    assert created_file.exists()

    detail_response = client.get(f"/api/v1/principles/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["name"] == "Design Sprint Principles"
    assert detail["content"].startswith("# Design Sprint Principles")

    update_payload = {"content": "# Design Sprint Principles\n\n1. **Focus**\n   Stay aligned."}
    update_response = client.put(
        f"/api/v1/principles/{created['id']}", json=update_payload
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert "Focus" in updated["content"]

    delete_response = client.delete(f"/api/v1/principles/{created['id']}")
    assert delete_response.status_code == 204
    assert not created_file.exists()
