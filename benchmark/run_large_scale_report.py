"""Generate a diagnostic report for every Pokemon answer in the local dataset.

This does not alter ranking rules. It measures the current baseline at scale so
we can make tuning decisions from distributions, not a few hand-picked examples.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from run_benchmark import (
    ability_document,
    attribute_score,
    cosine_rows,
    document,
    eligible,
    learnset_breadth_adjustment,
    move_relationship_scores,
    move_document,
    pokemon_document,
    relationship_score,
    title,
)


ROOT = Path(__file__).parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

# A broad, fixed reading set. Aggregate statistics still cover every answer.
SAMPLE_ANSWERS = [
    "bulbasaur", "charizard", "butterfree", "pikachu", "gengar", "onix", "lapras", "eevee", "snorlax", "ditto",
    "tyranitar", "blaziken", "gardevoir", "metagross", "rayquaza", "lucario", "garchomp", "rotom", "zoroark", "chandelure",
    "greninja", "sylveon", "aegislash", "mimikyu", "toxtricity", "corviknight", "dragapult", "tinkaton", "ceruledge", "ogerpon",
]


def percentile(values: list[int], value: float) -> int:
    if not values:
        return 0
    return int(round(float(np.percentile(values, value))))


def rank_answer(answer: dict, candidates: list[dict], candidate_vectors: np.ndarray, vector_by_id: dict[str, np.ndarray], stat_ranges: dict, weights: dict, scope: str, move_scores: dict[str, float], type_score: float, matching_move_type_score: float, learnset_breadth: dict[str, float]) -> list[dict]:
    semantic_scores = cosine_rows(vector_by_id[answer["id"]], candidate_vectors)
    rows = []
    for candidate, semantic in zip(candidates, semantic_scores):
        relation = relationship_score(answer, candidate, scope, move_scores, type_score, learnset_breadth)
        attribute = attribute_score(answer, candidate, stat_ranges, matching_move_type_score)
        score = weights["semantic"] * float(semantic) + weights["relationship"] * relation + weights["attribute"] * attribute
        rows.append({
            "id": candidate["id"], "name": candidate["name"], "category": candidate["category"],
            "semantic": float(semantic), "relationship": relation, "attribute": attribute, "score": score,
        })
    rows.sort(key=lambda row: (row["id"] != answer["id"], -row["score"], -row["semantic"], -row["relationship"], row["id"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def report_scope(scope: str, pokemon: list[dict], all_entities: list[dict], vectors: np.ndarray, vector_by_id: dict[str, np.ndarray], stat_ranges: dict, weights: dict, move_floor: float, type_score: float, matching_move_type_score: float, learnset_config: dict) -> str:
    candidates = [entity for entity in all_entities if eligible(entity, scope)]
    candidate_vectors = np.asarray([vector_by_id[entity["id"]] for entity in candidates])
    answers = [entity for entity in pokemon if eligible(entity, scope)]
    move_scores = move_relationship_scores(pokemon, scope, move_floor)
    learnset_breadth = {
        answer["id"]: learnset_breadth_adjustment(answer, scope, learnset_config["reference_move_count"], learnset_config["floor"])
        for answer in answers
    }
    evolution_ranks: list[int] = []
    ability_ranks: list[int] = []
    type_ranks: list[int] = []
    move_ranks: list[int] = []
    top25_categories: Counter[str] = Counter()
    samples: dict[str, list[dict]] = {}
    rank_uniqueness_failures = 0

    for index, answer in enumerate(answers, start=1):
        rows = rank_answer(answer, candidates, candidate_vectors, vector_by_id, stat_ranges, weights, scope, move_scores, type_score, matching_move_type_score, learnset_breadth)
        if len({row["rank"] for row in rows}) != len(rows):
            rank_uniqueness_failures += 1
        by_id = {row["id"]: row for row in rows}
        for relative in answer["evolution_family"]:
            if relative != answer["name"] and f"pokemon:{relative}" in by_id:
                evolution_ranks.append(by_id[f"pokemon:{relative}"]["rank"])
        for ability in answer["abilities"]:
            row = by_id.get(f"ability:{ability}")
            if row:
                ability_ranks.append(row["rank"])
        for pokemon_type in answer["types"]:
            row = by_id.get(f"type:{pokemon_type}")
            if row:
                type_ranks.append(row["rank"])
        for move, generations in answer["move_learnset_generations"].items():
            if scope == "all-goes" or any(generation <= 5 for generation in generations):
                row = by_id.get(f"move:{move}")
                if row:
                    move_ranks.append(row["rank"])
        top25_categories.update(row["category"] for row in rows[:25])
        if answer["name"] in SAMPLE_ANSWERS:
            samples[answer["name"]] = rows[:12]
        if index % 100 == 0 or index == len(answers):
            print(f"{scope}: ranked {index}/{len(answers)} answers", flush=True)

    def distribution(label: str, values: list[int]) -> str:
        return (
            f"- {label}: {len(values):,} comparisons; median rank **#{percentile(values, 50):,}**; "
            f"P25 **#{percentile(values, 25):,}**; P75 **#{percentile(values, 75):,}**; P90 **#{percentile(values, 90):,}**"
        )

    lines = [
        f"## {scope.replace('-', ' ').title()}",
        "",
        f"- Answer Pokémon tested: **{len(answers):,}**",
        f"- Eligible guesses per answer: **{len(candidates):,}**",
        f"- Unique-rank failures: **{rank_uniqueness_failures}**",
        "",
        "### Direct-relationship rank distributions",
        "",
        distribution("Other members of the answer's evolution family", evolution_ranks),
        distribution("Abilities the answer can have", ability_ranks),
        distribution("Types the answer has", type_ranks),
        distribution("Moves the answer can learn", move_ranks),
        "",
        "### Top-25 composition",
        "",
        f"- Pokémon: **{top25_categories['pokemon']:,}** ({top25_categories['pokemon'] / (len(answers) * 25):.1%})",
        f"- Moves: **{top25_categories['move']:,}** ({top25_categories['move'] / (len(answers) * 25):.1%})",
        f"- Abilities: **{top25_categories['ability']:,}** ({top25_categories['ability'] / (len(answers) * 25):.1%})",
        f"- Types: **{top25_categories['type']:,}** ({top25_categories['type'] / (len(answers) * 25):.1%})",
        "",
        "### Sample rankings",
        "",
    ]
    for answer in SAMPLE_ANSWERS:
        if answer not in samples:
            continue
        lines.extend([f"#### {title(answer)}", "", "| Rank | Guess | Category | Score | Semantic | Relation | Attribute |", "|---:|---|---|---:|---:|---:|---:|"])
        for row in samples[answer]:
            lines.append(f"| {row['rank']} | {title(row['name'])} | {row['category']} | {row['score']:.3f} | {row['semantic']:.3f} | {row['relationship']:.2f} | {row['attribute']:.3f} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    source = json.loads((DATA / "entities.json").read_text(encoding="utf-8"))
    all_entities = [entity for group in source.values() for entity in group]
    pokemon = source["pokemon"]
    print(f"Loading local embedding model: {config['model']}", flush=True)
    model = SentenceTransformer(config["model"])
    print(f"Embedding {len(all_entities)} entities...", flush=True)
    vectors = np.asarray(model.encode([document(entity) for entity in all_entities], normalize_embeddings=True, batch_size=512, show_progress_bar=True), dtype=np.float32)
    vector_by_id = {entity["id"]: vectors[index] for index, entity in enumerate(all_entities)}
    stat_ranges = {key: (min(p["stats"][key] for p in pokemon), max(p["stats"][key] for p in pokemon)) for key in pokemon[0]["stats"]}
    REPORTS.mkdir(exist_ok=True)
    report = [
        f"# PokeTox Daily Poketexto — large-scale {config['profile']} report",
        "",
        "This is a diagnostic run using rarity-adjusted direct move relationships. A move learned by many Pokemon receives less relationship credit than a rare learnset relationship. It is not a final ranking model.",
        "",
    ]
    for scope in ("all-goes", "gen-1-5"):
        report.append(report_scope(scope, pokemon, all_entities, vectors, vector_by_id, stat_ranges, config["weights"], config["move_relationship"]["floor"], config["type_relationship_score"], config["matching_move_type_attribute_score"], config["learnset_breadth"]))
        report.append("")
    output = REPORTS / f"large-scale-{config['profile']}.md"
    output.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {output}", flush=True)


if __name__ == "__main__":
    main()
