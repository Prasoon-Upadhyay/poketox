"""Run the first deterministic, local Daily Poketexto ranking benchmark."""

from __future__ import annotations

import csv
import json
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


def document(entity: dict) -> str:
    return {"pokemon": pokemon_document, "move": move_document, "ability": ability_document}[entity["category"]](entity)


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


def attribute_score(answer: dict, guess: dict, stat_ranges: dict[str, tuple[int, int]]) -> float:
    if guess["category"] == "pokemon":
        shared_types = len(set(answer["types"]) & set(guess["types"]))
        type_score = shared_types / max(len(set(answer["types"]) | set(guess["types"])), 1)
        family_score = float(bool(set(answer["evolution_family"]) & set(guess["evolution_family"])))
        return 0.45 * type_score + 0.35 * family_score + 0.20 * stat_similarity(answer, guess, stat_ranges)
    if guess["category"] == "move":
        return float(guess["type"] in answer["types"])
    return 0.0


def relationship_score(answer: dict, guess: dict, scope: str) -> float:
    if guess["category"] == "pokemon":
        return float(bool(set(answer["evolution_family"]) & set(guess["evolution_family"])))
    if guess["category"] == "move":
        if scope == "all-goes":
            return float(guess["name"] in answer["moves"])
        return float(any(generation <= 5 for generation in answer["move_learnset_generations"].get(guess["name"], [])))
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
        rows: list[dict] = []
        for answer_name in config["answers"]:
            answer = answers[answer_name]
            if not eligible(answer, scope):
                continue
            semantic = cosine_rows(vector_by_id[answer["id"]], np.asarray([vector_by_id[c["id"]] for c in candidates]))
            scored = []
            for candidate, semantic_score in zip(candidates, semantic):
                relation = relationship_score(answer, candidate, scope)
                attribute = attribute_score(answer, candidate, stat_ranges)
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

        report = REPORTS / f"{scope}.csv"
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
