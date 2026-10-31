"""Run the first deterministic, local Daily Poketexto ranking benchmark."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


def title(value: str) -> str:
    return value.replace("-", " ").title()


def pokemon_document(entity: dict) -> str:
    stats = ", ".join(f"{key} {value}" for key, value in entity["stats"].items())
    family = ", ".join(title(name) for name in entity["evolution_family"])
    return (
        f"{title(entity['name'])} is a Pokemon introduced in Generation {entity['generation']}. "
        f"Types: {', '.join(title(t) for t in entity['types'])}. "
        f"Pokedex number: {entity['pokedex_number']}. Evolution family: {family}. "
        f"Base stats: {stats}. Height {entity['height']} decimetres. Weight {entity['weight']} hectograms. "
        f"Pokedex identity: {entity['description']}"
    )


def move_document(entity: dict) -> str:
    return (
        f"{title(entity['name'])} is a {title(entity['type'])}-type {entity['damage_class']} Pokemon move "
        f"introduced in Generation {entity['generation']}. Power: {entity['power']}. Accuracy: {entity['accuracy']}. "
        f"Description: {entity['description']}"
    )


def ability_document(entity: dict) -> str:
    return (
        f"{title(entity['name'])} is a Pokemon ability introduced in Generation {entity['generation']}. "
        f"Description: {entity['description']}"
    )


def type_document(entity: dict) -> str:
    return f"{title(entity['name'])} is a Pokemon type introduced in Generation {entity['generation']}."


def document(entity: dict) -> str:
    return {"pokemon": pokemon_document, "move": move_document, "ability": ability_document, "type": type_document}[entity["category"]](entity)


def cosine_rows(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query_norm = np.linalg.norm(query)
    matrix_norm = np.linalg.norm(matrix, axis=1)
    return (matrix @ query) / np.maximum(matrix_norm * query_norm, 1e-12)


def stat_similarity(answer: dict, guess: dict, stat_ranges: dict[str, tuple[int, int]]) -> float:
    values = []
    for key, (low, high) in stat_ranges.items():
        span = max(high - low, 1)
        values.append(abs(answer["stats"][key] - guess["stats"][key]) / span)
    return max(0.0, 1.0 - float(np.mean(values)))


def attribute_score(answer: dict, guess: dict, stat_ranges: dict[str, tuple[int, int]], matching_move_type_score: float) -> float:
    if guess["category"] == "pokemon":
        shared_types = len(set(answer["types"]) & set(guess["types"]))
        type_score = shared_types / max(len(set(answer["types"]) | set(guess["types"])), 1)
        family_score = float(bool(set(answer["evolution_family"]) & set(guess["evolution_family"])))
        return 0.45 * type_score + 0.35 * family_score + 0.20 * stat_similarity(answer, guess, stat_ranges)
    if guess["category"] == "move":
        return matching_move_type_score if guess["type"] in answer["types"] else 0.0
    return 0.0


def move_relationship_scores(pokemon: list[dict], scope: str, floor: float) -> dict[str, float]:
    """Return a scoped, rarity-adjusted score for each learnable move.

    A move learned by one eligible Pokemon receives 1.0. A move learned by
    every eligible Pokemon receives `floor`; other moves fall smoothly between
    those values on a logarithmic curve. This reduces generic TM-style moves
    without discarding factual learnset relationships.
    """
    eligible_pokemon = [entity for entity in pokemon if eligible(entity, scope)]
    frequencies: Counter[str] = Counter()
    for entity in eligible_pokemon:
        for move, generations in entity["move_learnset_generations"].items():
            if scope == "all-goes" or any(generation <= 5 for generation in generations):
                frequencies[move] += 1
    total = len(eligible_pokemon)
    denominator = math.log((total + 1) / 2)
    return {
        move: floor + (1 - floor) * math.log((total + 1) / (frequency + 1)) / denominator
        for move, frequency in frequencies.items()
    }


def relationship_score(answer: dict, guess: dict, scope: str, move_scores: dict[str, float], type_score: float) -> float:
    if guess["category"] == "pokemon":
        return float(bool(set(answer["evolution_family"]) & set(guess["evolution_family"])))
    if guess["category"] == "move":
        if scope == "all-goes":
            return move_scores.get(guess["name"], 0.0) if guess["name"] in answer["moves"] else 0.0
        is_learnable = any(generation <= 5 for generation in answer["move_learnset_generations"].get(guess["name"], []))
        return move_scores.get(guess["name"], 0.0) if is_learnable else 0.0
    if guess["category"] == "type":
        return type_score if guess["name"] in answer["types"] else 0.0
    return float(guess["name"] in answer["abilities"])


def eligible(entity: dict, scope: str) -> bool:
    return scope == "all-goes" or entity["generation"] <= 5


def main() -> None:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    source = json.loads((DATA / "entities.json").read_text(encoding="utf-8"))
    all_entities = [entity for group in source.values() for entity in group]
    pokemon = source["pokemon"]
    answers = {entity["name"]: entity for entity in pokemon}
    missing = [name for name in config["answers"] if name not in answers]
    if missing:
        raise ValueError(f"Answers absent from dataset: {', '.join(missing)}")

    print(f"Loading local embedding model: {config['model']}")
    model = SentenceTransformer(config["model"])
    print(f"Embedding {len(all_entities)} entities...")
    vectors = model.encode(
        [document(entity) for entity in all_entities],
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=512,
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    vector_by_id = {entity["id"]: vectors[index] for index, entity in enumerate(all_entities)}
    stat_ranges = {
        key: (min(p["stats"][key] for p in pokemon), max(p["stats"][key] for p in pokemon))
        for key in pokemon[0]["stats"]
    }
    weights = config["weights"]
    REPORTS.mkdir(exist_ok=True)

    for scope in ("all-goes", "gen-1-5"):
        candidates = [entity for entity in all_entities if eligible(entity, scope)]
        move_scores = move_relationship_scores(pokemon, scope, config["move_relationship"]["floor"])
        rows: list[dict] = []
        for answer_name in config["answers"]:
            answer = answers[answer_name]
            if not eligible(answer, scope):
                continue
            semantic = cosine_rows(vector_by_id[answer["id"]], np.asarray([vector_by_id[c["id"]] for c in candidates]))
            scored = []
            for candidate, semantic_score in zip(candidates, semantic):
                relation = relationship_score(answer, candidate, scope, move_scores, config["type_relationship_score"])
                attribute = attribute_score(answer, candidate, stat_ranges, config["matching_move_type_attribute_score"])
                final = weights["semantic"] * float(semantic_score) + weights["relationship"] * relation + weights["attribute"] * attribute
                scored.append({
                    "answer": answer["name"], "guess": candidate["name"], "guess_id": candidate["id"],
                    "category": candidate["category"], "semantic": round(float(semantic_score), 6),
                    "relationship": relation, "attribute": round(attribute, 6), "final": round(final, 6),
                })
            scored.sort(key=lambda row: (row["guess_id"] != answer["id"], -row["final"], -row["semantic"], -row["relationship"], row["guess_id"]))
            for rank, row in enumerate(scored, start=1):
                row["rank"] = rank
            rows.extend(scored)

        report = REPORTS / f"{scope}-{config['profile']}.csv"
        with report.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["answer", "rank", "guess", "category", "semantic", "relationship", "attribute", "final", "guess_id"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {report} ({len(rows)} ranked entries)")
        for answer_name in config["answers"]:
            sample = [row for row in rows if row["answer"] == answer_name][: config["top_results"]]
            if sample:
                print(f"\n{scope}: {title(answer_name)}")
                for row in sample[:10]:
                    print(f"#{row['rank']:>3} {title(row['guess']):<25} {row['category']:<7} score={row['final']:.3f}")


if __name__ == "__main__":
    main()
