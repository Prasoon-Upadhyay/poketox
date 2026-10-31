from fastapi.testclient import TestClient

from poketox_api.main import app


def start_game(client: TestClient) -> None:
    response = client.post("/api/v1/daily/start", json={"generations": [1, 2, 3, 4, 5]})
    assert response.status_code == 200


def test_public_daily_metadata_does_not_leak_target() -> None:
    with TestClient(app) as client:
        start_game(client)
        response = client.get("/api/v1/daily")
    assert response.status_code == 200
    assert "target" not in response.json()


def test_reset_starts_a_new_hidden_staging_game() -> None:
    with TestClient(app) as client:
        start_game(client)
        daily = client.get("/api/v1/daily").json()
        reset = client.post("/api/v1/daily/reset", json={"generations": [1, 2, 3, 4, 5]})
    assert reset.status_code == 200
    assert reset.json()["puzzle_id"] != daily["puzzle_id"]
    assert "target" not in reset.json()


def test_give_up_reveals_the_current_random_target() -> None:
    with TestClient(app) as client:
        start_game(client)
        response = client.post("/api/v1/daily/give-up")
    assert response.status_code == 200
    assert response.json()["target"]["id"].startswith("pokemon:")


def test_suggestions_and_canonical_guess() -> None:
    with TestClient(app) as client:
        start_game(client)
        target = client.post("/api/v1/daily/give-up").json()["target"]
        response = client.post("/api/v1/daily/guesses", json=target)
    assert response.status_code == 200
    assert response.json()["rank"] == 1
    assert response.json()["solved"] is True


def test_mismatched_display_metadata_is_rejected() -> None:
    with TestClient(app) as client:
        start_game(client)
        response = client.post("/api/v1/daily/guesses", json={"id": "move:psychic", "category": "type", "name": "psychic"})
    assert response.status_code == 422
    assert response.json()["status"] == "rejected"


def test_duplicate_guess_is_rejected() -> None:
    with TestClient(app) as client:
        start_game(client)
        target = client.post("/api/v1/daily/give-up").json()["target"]
        assert client.post("/api/v1/daily/guesses", json=target).status_code == 200
        duplicate = client.post("/api/v1/daily/guesses", json=target)
    assert duplicate.status_code == 409
    assert duplicate.json()["status"] == "rejected"
