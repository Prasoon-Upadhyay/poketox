from __future__ import annotations

import json
import re
import secrets
import threading
import uuid
from pathlib import Path

from fastapi import HTTPException

from .ranking import rank_answer


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "benchmark" / "data" / "entities.json"


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


def available_in_generations(pokemon: dict, generations: set[int]) -> bool:
    """Use PokeAPI version-group learnset records as game-generation availability."""
    return any(
        any(generation in generations for generation in move_generations)
        for move_generations in pokemon["move_learnset_generations"].values()
    )


class DailyGame:
    """Mutable in-memory game configured from the frontend's generation selection."""

    def __init__(self) -> None:
        dataset_path = DEFAULT_DATASET
        if not dataset_path.is_file():
            raise RuntimeError(f"Dataset missing at {dataset_path}. Run python benchmark/build_dataset.py first.")
        source = json.loads(dataset_path.read_text(encoding="utf-8"))
        self.all_entities = [entity for group in source.values() for entity in group]
        self.pokemon = source["pokemon"]
        self.by_id = {entity["id"]: entity for entity in self.all_entities}
        self.generations: set[int] = set()
        self.candidates: list[dict] = []
        self.eligible_pokemon: list[dict] = []
        self.lock = threading.RLock()
        self.target: dict | None = None
        self.rankings: dict[str, dict] = {}
        self.puzzle_id: str | None = None
        self.guessed_ids: set[str]
        self.guessed_ids = set()

    def refresh(self, generations: list[int]) -> None:
        """Select a target and calculate a rank table for the requested generations."""
        with self.lock:
            selected = set(generations)
            if len(selected) != len(generations) or not selected or not selected.issubset(set(range(1, 10))):
                raise HTTPException(422, detail="generations must contain unique values from 1 through 9.")
            previous_target = self.target if selected == self.generations else None
            self.generations = selected
            self.eligible_pokemon = [entity for entity in self.pokemon if available_in_generations(entity, self.generations)]
            learnable_moves = {
                move
                for pokemon in self.eligible_pokemon
                for move, move_generations in pokemon["move_learnset_generations"].items()
                if any(generation in self.generations for generation in move_generations)
            }
            available_abilities = {ability for pokemon in self.eligible_pokemon for ability in pokemon["abilities"]}
            self.candidates = [
                entity for entity in self.all_entities
                if (entity["category"] == "pokemon" and available_in_generations(entity, self.generations))
                or entity["category"] == "type"
                or (entity["category"] == "move" and entity["name"] in learnable_moves)
                or (entity["category"] == "ability" and entity["name"] in available_abilities)
            ]
            choices = [entity for entity in self.eligible_pokemon if previous_target is None or entity["id"] != previous_target["id"]]
            self.target = secrets.choice(choices)
            self.rankings = rank_answer(self.target, self.candidates, self.eligible_pokemon, self.generations)
            self.puzzle_id = f"staging-{uuid.uuid4().hex[:12]}"
            self.guessed_ids = set()

    def suggestion_list(self, query: str, limit: int) -> list[dict]:
        needle = normalize(query)
        with self.lock:
            self._ensure_started()
            matches = [entity for entity in self.candidates if needle in normalize(entity["name"])]
            matches.sort(key=lambda entity: (not normalize(entity["name"]).startswith(needle), entity["category"], entity["name"]))
            return [suggestion_for(entity) for entity in matches[:limit]]

    def submit(self, entity_id: str, category: str | None, name: str | None) -> dict:
        with self.lock:
            self._ensure_started()
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
            self._ensure_started()
            return {"puzzle_id": self.puzzle_id, "generations": sorted(self.generations), "categories": ["pokemon", "move", "ability", "type"]}

    def reveal_target(self) -> dict:
        """Return the answer only after an explicit give-up action."""
        with self.lock:
            self._ensure_started()
            return {"status": "given_up", "puzzle_id": self.puzzle_id, "target": suggestion_for(self.target)}

    def _ensure_started(self) -> None:
        if self.target is None or self.puzzle_id is None:
            raise HTTPException(409, detail="Start a game with a generation selection first.")
