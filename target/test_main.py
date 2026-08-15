import sqlite3

import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "tasks.db")
    with TestClient(app) as test_client:
        yield test_client


def test_seed_runs_once(client):
    assert len(client.get("/tasks").json()) == 3
    database.initialize_database()
    assert len(client.get("/tasks").json()) == 3


def test_read_endpoints(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json()[0] == {
        "id": 1,
        "title": "Learn FastAPI",
        "done": False,
    }
    missing = client.get("/tasks/999")
    assert missing.status_code == 404
    assert missing.json() == {"error": "Task not found"}


def test_create_and_persist_task(client):
    invalid = client.post("/tasks", json={"title": " "})
    assert invalid.status_code == 400
    created = client.post("/tasks", json={"title": "Write tests"})
    assert created.status_code == 201
    assert created.json() == {"id": 4, "title": "Write tests", "done": False}
    with sqlite3.connect(database.DATABASE_PATH) as connection:
        row = connection.execute(
            "SELECT title, done FROM tasks WHERE id = ?",
            (4,),
        ).fetchone()
    assert row == ("Write tests", 0)


def test_update_and_delete_task(client):
    updated = client.put(
        "/tasks/1",
        json={"title": "Learn SQLite", "done": True},
    )
    assert updated.status_code == 200
    assert updated.json() == {"id": 1, "title": "Learn SQLite", "done": True}
    deleted = client.delete("/tasks/1")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get("/tasks/1").status_code == 404


def test_update_and_delete_unknown_task(client):
    updated = client.put(
        "/tasks/999",
        json={"title": "Missing", "done": False},
    )
    assert updated.status_code == 404
    assert updated.json() == {"error": "Task not found"}
    deleted = client.delete("/tasks/999")
    assert deleted.status_code == 404
    assert deleted.json() == {"error": "Task not found"}


def test_update_validation(client):
    response = client.put("/tasks/1", json={"title": "", "done": "yes"})
    assert response.status_code == 400
    assert response.json() == {
        "error": "Valid title and done values are required"
    }

