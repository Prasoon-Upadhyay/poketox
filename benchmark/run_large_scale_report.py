"""Generate the large-scale report for the structured-facts benchmark."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from run_benchmark import eligible, learnset_breadth_adjustment, move_relationship_scores, rank_answer, title


ROOT = Path(__file__).parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

SAMPLE_ANSWERS = [
    "bulbasaur", "charizard", "butterfree", "pikachu", "gengar", "onix", "lapras", "eevee", "snorlax", "ditto",
    "tyranitar", "blaziken", "gardevoir", "metagross", "rayquaza", "lucario", "garchomp", "rotom", "zoroark", "chandelure",
    "greninja", "sylveon", "aegislash", "mimikyu", "toxtricity", "corviknight", "dragapult", "tinkaton", "ceruledge", "ogerpon",
]


def percentile(values: list[int], percent: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percent / 100)
    return ordered[index]


def report_scope(scope: str, pokemon: list[dict], all_entities: list[dict], config: dict, stat_ranges: dict) -> str:
    candidates = [entity for entity in all_entities if eligible(entity, scope)]
    answers = [entity for entity in pokemon if eligible(entity, scope)]
    move_scores = move_relationship_scores(pokemon, scope, config["move_relationship"]["floor"])
    evolution_ranks, ability_ranks, type_ranks, move_ranks = [], [], [], []
    top25_categories: Counter[str] = Counter()
    samples: dict[str, list[dict]] = {}
    rank_failures = 0

    for index, answer in enumerate(answers, start=1):
        breadth = learnset_breadth_adjustment(answer, scope, config["learnset_breadth"]["reference_move_count"], config["learnset_breadth"]["floor"])
        rows = rank_answer(answer, candidates, scope, move_scores, breadth, stat_ranges, config["scoring"])
        if len({row["rank"] for row in rows}) != len(rows):
            rank_failures += 1
        by_id = {row["id"]: row for row in rows}
        for relative in answer["evolution_family"]:
            if relative != answer["name"] and f"pokemon:{relative}" in by_id:
                evolution_ranks.append(by_id[f"pokemon:{relative}"]["rank"])
        for ability in answer["abilities"]:
            if f"ability:{ability}" in by_id:
                ability_ranks.append(by_id[f"ability:{ability}"]["rank"])
        for pokemon_type in answer["types"]:
            if f"type:{pokemon_type}" in by_id:
                type_ranks.append(by_id[f"type:{pokemon_type}"]["rank"])
        for move, generations in answer["move_learnset_generations"].items():
            if (scope == "all-goes" or any(generation <= 5 for generation in generations)) and f"move:{move}" in by_id:
                move_ranks.append(by_id[f"move:{move}"]["rank"])
        top25_categories.update(row["category"] for row in rows[:25])
        if answer["name"] in SAMPLE_ANSWERS:
            samples[answer["name"]] = rows[:30]
        if index % 100 == 0 or index == len(answers):
            print(f"{scope}: ranked {index}/{len(answers)} answers", flush=True)

    def distribution(label: str, values: list[int]) -> str:
        return f"- {label}: {len(values):,} comparisons; median **#{percentile(values, 50):,}**; P25 **#{percentile(values, 25):,}**; P75 **#{percentile(values, 75):,}**; P90 **#{percentile(values, 90):,}**"

    lines = [
        f"## {scope.replace('-', ' ').title()}", "",
        f"- Answer Pokemon tested: **{len(answers):,}**",
        f"- Eligible guesses per answer: **{len(candidates):,}**",
        f"- Unique-rank failures: **{rank_failures}**", "",
        "### Direct-relationship rank distributions", "",
        distribution("Other evolution-family Pokemon", evolution_ranks),
        distribution("Abilities the answer can have", ability_ranks),
        distribution("Types the answer has", type_ranks),
        distribution("Moves the answer can learn", move_ranks), "",
        "### Top-25 composition", "",
        f"- Pokemon: **{top25_categories['pokemon']:,}** ({top25_categories['pokemon'] / (len(answers) * 25):.1%})",
        f"- Moves: **{top25_categories['move']:,}** ({top25_categories['move'] / (len(answers) * 25):.1%})",
        f"- Abilities: **{top25_categories['ability']:,}** ({top25_categories['ability'] / (len(answers) * 25):.1%})",
        f"- Types: **{top25_categories['type']:,}** ({top25_categories['type'] / (len(answers) * 25):.1%})", "",
        "### Sample rankings", "",
    ]
    for answer_name in SAMPLE_ANSWERS:
        if answer_name not in samples:
            continue
        lines.extend([f"#### {title(answer_name)}", "", "| Rank | Guess | Category | Score | Reason |", "|---:|---|---|---:|---|"])
        for row in samples[answer_name]:
            lines.append(f"| {row['rank']} | {title(row['name'])} | {row['category']} | {row['final']:.3f} | {row['reason']} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    source = json.loads((DATA / "entities.json").read_text(encoding="utf-8"))
    all_entities = [entity for group in source.values() for entity in group]
    pokemon = source["pokemon"]
    stat_ranges = {key: (min(p["stats"][key] for p in pokemon), max(p["stats"][key] for p in pokemon)) for key in pokemon[0]["stats"]}
    REPORTS.mkdir(exist_ok=True)
    report = [
        f"# PokeTox Daily Poketexto — large-scale {config['profile']} report", "",
        "This benchmark uses only direct, explainable facts: evolution family, types, abilities, learnsets, and a small same-type stat tie-breaker. It does not use embeddings.", "",
    ]
    for scope in ("all-goes", "gen-1-5"):
        report.extend([report_scope(scope, pokemon, all_entities, config, stat_ranges), ""])
    output = REPORTS / f"large-scale-{config['profile']}.md"
    output.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {output}", flush=True)


if __name__ == "__main__":
    main()
