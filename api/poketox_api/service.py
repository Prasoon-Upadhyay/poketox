from __future__ import annotations

import json
import re
import secrets
import threading
import uuid
from pathlib import Path

from fastapi import HTTPException

from .ranking import eligible, rank_answer


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "benchmark" / "data" / "entities.json"
TEST_GENERATIONS = [1, 2, 3, 4, 5]


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def suggestion_for(entity: dict) -> dict:
    """Expose only display metadata needed by the suggestion dropdown."""
    suggestion = {"id": entity["id"], "category": entity["category"], "name": entity["name"], "types": [], "move_type": None, "damage_class": None, "power": None, "sprite_id": None}
    if entity["category"] == "pokemon":
        suggestion.update({"types": entity["types"], "sprite_id": entity["pokedex_number"]})
    elif entity["category"] == "move":
        suggestion.update({"types": [entity["type"]], "move_type": entity["type"], "damage_class": entity["damage_class"], "power": entity["power"]})
    elif entity["category"] == "type":
        suggestion["types"] = [entity["name"]]
    return suggestion


class DailyGame:
    """Mutable in-memory staging game with a random target from test generations."""

    def __init__(self) -> None:
        dataset_path = DEFAULT_DATASET
        if not dataset_path.is_file():
            raise RuntimeError(f"Dataset missing at {dataset_path}. Run python benchmark/build_dataset.py first.")
        source = json.loads(dataset_path.read_text(encoding="utf-8"))
        self.generations = set(TEST_GENERATIONS)
        self.all_entities = [entity for group in source.values() for entity in group]
        self.pokemon = source["pokemon"]
        self.by_id = {entity["id"]: entity for entity in self.all_entities}
        self.candidates = [entity for entity in self.all_entities if eligible(entity, self.generations)]
        self.eligible_pokemon = [entity for entity in self.pokemon if eligible(entity, self.generations)]
        self.lock = threading.RLock()
        self.target: dict
        self.rankings: dict[str, dict]
        self.puzzle_id: str
        self.guessed_ids: set[str]
        self.refresh()

    def refresh(self) -> None:
        """Select a different eligible target and calculate its rank table."""
        with self.lock:
            choices = [entity for entity in self.eligible_pokemon if getattr(self, "target", None) is None or entity["id"] != self.target["id"]]
            self.target = secrets.choice(choices)
            self.rankings = rank_answer(self.target, self.candidates, self.pokemon, self.generations)
            self.puzzle_id = f"staging-{uuid.uuid4().hex[:12]}"
            self.guessed_ids = set()

    def suggestion_list(self, query: str, limit: int) -> list[dict]:
        needle = normalize(query)
        with self.lock:
            matches = [entity for entity in self.candidates if needle in normalize(entity["name"])]
            matches.sort(key=lambda entity: (not normalize(entity["name"]).startswith(needle), entity["category"], entity["name"]))
            return [suggestion_for(entity) for entity in matches[:limit]]

    def submit(self, entity_id: str, category: str | None, name: str | None) -> dict:
        with self.lock:
            entity = self.by_id.get(entity_id)
            if not entity:
                raise HTTPException(422, detail="That entity ID is not recognised.")
            if entity_id not in self.rankings:
                raise HTTPException(422, detail="That entity is outside the current test generations.")
            if category is not None and category != entity["category"]:
                raise HTTPException(422, detail="category does not match the selected entity ID.")
            if name is not None and normalize(name) != normalize(entity["name"]):
                raise HTTPException(422, detail="name does not match the selected entity ID.")
            if entity_id in self.guessed_ids:
                raise HTTPException(409, detail="You've already guessed that entity.")
            row = self.rankings[entity_id]
            self.guessed_ids.add(entity_id)
            return {"status": "accepted", "guess": suggestion_for(entity), "rank": row["rank"], "solved": entity_id == self.target["id"]}

    def public_metadata(self) -> dict:
        """Build the response used when a client starts or resets its local game."""
        with self.lock:
            return {"puzzle_id": self.puzzle_id, "generations": TEST_GENERATIONS, "categories": ["pokemon", "move", "ability", "type"]}

    def reveal_target(self) -> dict:
        """Return the answer only after an explicit give-up action."""
        with self.lock:
            return {"status": "given_up", "puzzle_id": self.puzzle_id, "target": suggestion_for(self.target)}
