"""The accepted V6 structured-facts ranker, isolated from benchmark experiments."""

from __future__ import annotations

import math
from collections import Counter


SCORING = {
    "exact_answer": 2.0,
    "evolution_family": 1.0,
    "shared_type_per_type": 0.20,
    "stat_tiebreaker": 0.04,
    "direct_type": 0.38,
    "direct_ability": 0.34,
    "learned_move_base": 0.18,
    "learned_move_range": 0.16,
    "off_type_move_base": 0.08,
    "off_type_move_range": 0.08,
}
MOVE_FLOOR = 0.6
LEARNSET_REFERENCE_COUNT = 40
LEARNSET_FLOOR = 0.65


def eligible(entity: dict, allowed_generations: set[int]) -> bool:
    """Keep only entities introduced in the active test-generation set."""
    return entity["generation"] in allowed_generations


def move_relationship_scores(pokemon: list[dict], allowed_generations: set[int]) -> dict[str, float]:
    eligible_pokemon = [entity for entity in pokemon if eligible(entity, allowed_generations)]
    frequencies: Counter[str] = Counter()
    for entity in eligible_pokemon:
        for move, move_generations in entity["move_learnset_generations"].items():
            if any(generation in allowed_generations for generation in move_generations):
                frequencies[move] += 1
    denominator = math.log((len(eligible_pokemon) + 1) / 2)
    return {
        move: MOVE_FLOOR + (1 - MOVE_FLOOR) * math.log((len(eligible_pokemon) + 1) / (count + 1)) / denominator
        for move, count in frequencies.items()
    }


def rank_answer(answer: dict, candidates: list[dict], pokemon: list[dict], allowed_generations: set[int]) -> dict[str, dict]:
    stat_ranges = {
        key: (min(entity["stats"][key] for entity in pokemon), max(entity["stats"][key] for entity in pokemon))
        for key in pokemon[0]["stats"]
    }
    move_scores = move_relationship_scores(pokemon, allowed_generations)
    learnset_count = sum(
        1 for move_generations in answer["move_learnset_generations"].values()
        if any(generation in allowed_generations for generation in move_generations)
    )
    breadth = 1.0 if learnset_count <= LEARNSET_REFERENCE_COUNT else max(
        LEARNSET_FLOOR, math.log(LEARNSET_REFERENCE_COUNT + 1) / math.log(learnset_count + 1)
    )

    def stat_similarity(guess: dict) -> float:
        differences = [
            abs(answer["stats"][key] - guess["stats"][key]) / max(high - low, 1)
            for key, (low, high) in stat_ranges.items()
        ]
        return max(0.0, 1.0 - sum(differences) / len(differences))

    rows: list[dict] = []
    for guess in candidates:
        relationship, attribute, reason = 0.0, 0.0, "no direct relationship"
        if guess["id"] == answer["id"]:
            relationship, reason = SCORING["exact_answer"], "exact answer"
        elif guess["category"] == "pokemon":
            shared = sorted(set(answer["types"]) & set(guess["types"]))
            if set(answer["evolution_family"]) & set(guess["evolution_family"]):
                relationship, reason = SCORING["evolution_family"], "same evolution family"
            if shared:
                attribute = SCORING["shared_type_per_type"] * len(shared) + SCORING["stat_tiebreaker"] * stat_similarity(guess)
                shared_reason = f"shares {', '.join(item.title() for item in shared)}"
                reason = f"{reason}; {shared_reason}" if relationship else shared_reason
        elif guess["category"] == "ability" and guess["name"] in answer["abilities"]:
            relationship, reason = SCORING["direct_ability"], "ability of target"
        elif guess["category"] == "type" and guess["name"] in answer["types"]:
            relationship, reason = SCORING["direct_type"], "type of target"
        elif guess["category"] == "move":
            learned = any(generation in allowed_generations for generation in answer["move_learnset_generations"].get(guess["name"], []))
            if learned:
                same_type = guess["type"] in answer["types"]
                base = SCORING["learned_move_base"] if same_type else SCORING["off_type_move_base"]
                spread = SCORING["learned_move_range"] if same_type else SCORING["off_type_move_range"]
                relationship = base + spread * move_scores[guess["name"]] * breadth
                reason = "same-type learned move; rarity-adjusted" if same_type else "off-type learned move; rarity-adjusted"
        rows.append({"id": guess["id"], "relationship": relationship, "attribute": attribute, "final": relationship + attribute, "reason": reason})
    rows.sort(key=lambda row: (row["id"] != answer["id"], -row["final"], -row["relationship"], -row["attribute"], row["id"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return {row["id"]: row for row in rows}
