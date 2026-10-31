"""Run the deterministic, structured-facts Daily Poketexto benchmark."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


def title(value: str) -> str:
    return value.replace("-", " ").title()


def eligible(entity: dict, scope: str) -> bool:
    return scope == "all-goes" or entity["generation"] <= 5


def stat_similarity(answer: dict, guess: dict, stat_ranges: dict[str, tuple[int, int]]) -> float:
    differences = [abs(answer["stats"][key] - guess["stats"][key]) / max(high - low, 1) for key, (low, high) in stat_ranges.items()]
    return max(0.0, 1.0 - sum(differences) / len(differences))


def move_relationship_scores(pokemon: list[dict], scope: str, floor: float) -> dict[str, float]:
    """Give uncommon learnset edges more credit than broad TM-style edges."""
    eligible_pokemon = [entity for entity in pokemon if eligible(entity, scope)]
    frequencies: Counter[str] = Counter()
    for entity in eligible_pokemon:
        for move, generations in entity["move_learnset_generations"].items():
            if scope == "all-goes" or any(generation <= 5 for generation in generations):
                frequencies[move] += 1
    total = len(eligible_pokemon)
    denominator = math.log((total + 1) / 2)
    return {move: floor + (1 - floor) * math.log((total + 1) / (count + 1)) / denominator for move, count in frequencies.items()}


def learnset_breadth_adjustment(answer: dict, scope: str, reference_move_count: int, floor: float) -> float:
    """Prevent a Pokemon with a huge learnset from promoting every move equally."""
    count = sum(1 for generations in answer["move_learnset_generations"].values() if scope == "all-goes" or any(generation <= 5 for generation in generations))
    return 1.0 if count <= reference_move_count else max(floor, math.log(reference_move_count + 1) / math.log(count + 1))


def is_learned(answer: dict, move_name: str, scope: str) -> bool:
    return move_name in answer["moves"] if scope == "all-goes" else any(generation <= 5 for generation in answer["move_learnset_generations"].get(move_name, []))


def score_guess(answer: dict, guess: dict, scope: str, move_scores: dict[str, float], breadth: float, stat_ranges: dict[str, tuple[int, int]], scoring: dict) -> dict:
    """Score only factual relationships that can be shown to the player."""
    relationship, attribute, reason = 0.0, 0.0, "no direct relationship"
    if guess["id"] == answer["id"]:
        return {"relationship": scoring["exact_answer"], "attribute": 0.0, "final": scoring["exact_answer"], "reason": "exact answer"}

    if guess["category"] == "pokemon":
        shared = sorted(set(answer["types"]) & set(guess["types"]))
        family = bool(set(answer["evolution_family"]) & set(guess["evolution_family"]))
        if family:
            relationship = scoring["evolution_family"]
            reason = "same evolution family"
        if shared:
            attribute = scoring["shared_type_per_type"] * len(shared) + scoring["stat_tiebreaker"] * stat_similarity(answer, guess, stat_ranges)
            type_reason = f"shares {', '.join(title(item) for item in shared)}"
            reason = f"{reason}; {type_reason}" if family else type_reason
    elif guess["category"] == "ability" and guess["name"] in answer["abilities"]:
        relationship, reason = scoring["direct_ability"], "ability of target"
    elif guess["category"] == "type" and guess["name"] in answer["types"]:
        relationship, reason = scoring["direct_type"], "type of target"
    elif guess["category"] == "move" and is_learned(answer, guess["name"], scope):
        same_type = guess["type"] in answer["types"]
        base = scoring["learned_move_base"] if same_type else scoring["off_type_move_base"]
        spread = scoring["learned_move_range"] if same_type else scoring["off_type_move_range"]
        relationship = base + spread * move_scores[guess["name"]] * breadth
        reason = "same-type learned move; rarity-adjusted" if same_type else "off-type learned move; rarity-adjusted"
    return {"relationship": relationship, "attribute": attribute, "final": relationship + attribute, "reason": reason}


def rank_answer(answer: dict, candidates: list[dict], scope: str, move_scores: dict[str, float], breadth: float, stat_ranges: dict[str, tuple[int, int]], scoring: dict) -> list[dict]:
    rows = [{"id": candidate["id"], "name": candidate["name"], "category": candidate["category"], **score_guess(answer, candidate, scope, move_scores, breadth, stat_ranges, scoring)} for candidate in candidates]
    rows.sort(key=lambda row: (row["id"] != answer["id"], -row["final"], -row["relationship"], -row["attribute"], row["id"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def main() -> None:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    source = json.loads((DATA / "entities.json").read_text(encoding="utf-8"))
    all_entities = [entity for group in source.values() for entity in group]
    pokemon = source["pokemon"]
    answers = {entity["name"]: entity for entity in pokemon}
    stat_ranges = {key: (min(p["stats"][key] for p in pokemon), max(p["stats"][key] for p in pokemon)) for key in pokemon[0]["stats"]}
    REPORTS.mkdir(exist_ok=True)
    for scope in ("all-goes", "gen-1-5"):
        candidates = [entity for entity in all_entities if eligible(entity, scope)]
        move_scores = move_relationship_scores(pokemon, scope, config["move_relationship"]["floor"])
        output = []
        for answer_name in config["answers"]:
            answer = answers[answer_name]
            if eligible(answer, scope):
                breadth = learnset_breadth_adjustment(answer, scope, config["learnset_breadth"]["reference_move_count"], config["learnset_breadth"]["floor"])
                output.extend({"answer": answer_name, **row} for row in rank_answer(answer, candidates, scope, move_scores, breadth, stat_ranges, config["scoring"]))
        report = REPORTS / f"{scope}-{config['profile']}.csv"
        with report.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["answer", "rank", "guess", "category", "reason", "relationship", "attribute", "final", "guess_id"])
            writer.writeheader()
            for row in output:
                writer.writerow({"answer": row["answer"], "rank": row["rank"], "guess": row["name"], "category": row["category"], "reason": row["reason"], "relationship": row["relationship"], "attribute": row["attribute"], "final": row["final"], "guess_id": row["id"]})
        print(f"Wrote {report} ({len(output)} ranked entries)")


if __name__ == "__main__":
    main()
