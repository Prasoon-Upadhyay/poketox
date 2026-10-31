"""Minimal local API for exercising the Daily Poketexto ranking engine.

Run from the repository root:
    python benchmark/test_api.py

This is intentionally a test server. It selects one random Gen 1-5 Pokemon at
startup and exposes that answer through a test-only endpoint.
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from run_benchmark import eligible, learnset_breadth_adjustment, move_relationship_scores, rank_answer


ROOT = Path(__file__).parent
DATA = ROOT / "data"
SCOPE = "gen-1-5"


def normalize(value: str) -> str:
    """Make case, whitespace, punctuation, and hyphens irrelevant for lookup."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


class Puzzle:
    def __init__(self) -> None:
        config_path = ROOT / "config.json"
        dataset_path = DATA / "entities.json"
        if not dataset_path.exists():
            raise FileNotFoundError("Dataset missing. Run: python benchmark/build_dataset.py")

        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        source = json.loads(dataset_path.read_text(encoding="utf-8"))
        self.all_entities = [entity for group in source.values() for entity in group]
        self.pokemon = source["pokemon"]
        self.candidates = [entity for entity in self.all_entities if eligible(entity, SCOPE)]
        self.target = secrets.choice([entity for entity in self.pokemon if eligible(entity, SCOPE)])
        self.stat_ranges = {
            key: (min(pokemon["stats"][key] for pokemon in self.pokemon), max(pokemon["stats"][key] for pokemon in self.pokemon))
            for key in self.pokemon[0]["stats"]
        }
        move_scores = move_relationship_scores(self.pokemon, SCOPE, self.config["move_relationship"]["floor"])
        breadth = learnset_breadth_adjustment(
            self.target,
            SCOPE,
            self.config["learnset_breadth"]["reference_move_count"],
            self.config["learnset_breadth"]["floor"],
        )
        self.rows_by_id = {
            row["id"]: row
            for row in rank_answer(self.target, self.candidates, SCOPE, move_scores, breadth, self.stat_ranges, self.config["scoring"])
        }
        self.all_by_normalized_name: dict[str, list[dict]] = {}
        self.all_by_id = {entity["id"]: entity for entity in self.all_entities}
        for entity in self.all_entities:
            self.all_by_normalized_name.setdefault(normalize(entity["name"]), []).append(entity)

    def resolve_id(self, entity_id: str) -> tuple[dict | None, str | None]:
        entity = self.all_by_id.get(entity_id)
        if not entity:
            return None, "That entity ID is not recognised."
        if entity["id"] not in self.rows_by_id:
            return None, "That entity is valid Pokemon data, but it is outside the current Gen 1-5 puzzle scope."
        return entity, None

    def resolve(self, guess: str, category: str | None) -> tuple[dict | None, str | None, list[dict] | None]:
        matches = self.all_by_normalized_name.get(normalize(guess), [])
        if category:
            matches = [entity for entity in matches if entity["category"] == category]
        eligible_matches = [entity for entity in matches if entity["id"] in self.rows_by_id]
        if not matches:
            return None, "That is not a recognised Pokemon, move, ability, or type.", None
        if not eligible_matches:
            return None, "That is valid Pokemon data, but it is outside the current Gen 1-5 puzzle scope.", None
        if len(eligible_matches) > 1:
            return None, "That guess is ambiguous. Send a category to choose the intended entity.", eligible_matches
        return eligible_matches[0], None, None


class Handler(BaseHTTPRequestHandler):
    puzzle: Puzzle

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path != "/api/test/target":
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "rejected", "message": "Use GET /api/test/target or POST /api/guess."})
            return
        target = self.puzzle.target
        self.send_json(HTTPStatus.OK, {
            "status": "ok",
            "scope": SCOPE,
            "target": {"id": target["id"], "name": target["name"], "category": target["category"]},
            "message": "Test-only endpoint. A production Daily puzzle must not reveal its target.",
        })

    def do_POST(self) -> None:
        if self.path != "/api/guess":
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "rejected", "message": "Use POST /api/guess."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"status": "rejected", "message": "Body must be valid JSON."})
            return
        entity_id = payload.get("id") if isinstance(payload, dict) else None
        guess = payload.get("guess") if isinstance(payload, dict) else None
        category = payload.get("category") if isinstance(payload, dict) else None
        if entity_id is not None:
            if not isinstance(entity_id, str) or not entity_id:
                self.send_json(HTTPStatus.BAD_REQUEST, {"status": "rejected", "message": "id must be a non-empty entity ID string."})
                return
            entity, rejection = self.puzzle.resolve_id(entity_id)
            if rejection:
                self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"status": "rejected", "message": rejection})
                return
            self.respond_to_guess(entity)
            return
        if not isinstance(guess, str) or not guess.strip():
            self.send_json(HTTPStatus.BAD_REQUEST, {"status": "rejected", "message": "Provide an entity id, or a non-empty string field named 'guess'."})
            return
        if category is not None and category not in {"pokemon", "move", "ability", "type"}:
            self.send_json(HTTPStatus.BAD_REQUEST, {"status": "rejected", "message": "category must be pokemon, move, ability, or type."})
            return

        entity, rejection, ambiguous = self.puzzle.resolve(guess, category)
        if rejection:
            response = {"status": "rejected", "message": rejection}
            if ambiguous:
                response["candidates"] = [{"name": item["name"], "category": item["category"]} for item in ambiguous]
            self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, response)
            return
        self.respond_to_guess(entity)

    def respond_to_guess(self, entity: dict) -> None:
        row = self.puzzle.rows_by_id[entity["id"]]
        self.send_json(HTTPStatus.OK, {
            "status": "accepted",
            "guess": {"id": entity["id"], "name": entity["name"], "category": entity["category"]},
            "rank": row["rank"],
            "reason": row["reason"],
            "solved": entity["id"] == self.puzzle.target["id"],
        })


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Daily Poketexto test API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    Handler.puzzle = Puzzle()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Daily Poketexto test API on http://{args.host}:{args.port}")
    print("Selected one random Gen 1-5 target for this server process.")
    server.serve_forever()


if __name__ == "__main__":
    main()
