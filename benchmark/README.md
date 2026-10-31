# Daily Poketexto benchmark

This is the first, deliberately simple ranking benchmark for PokeTox. It generates one local embedding per entity and ranks every eligible Pokemon, move, ability, and type for a small set of mystery Pokemon.

## Rules under test

`score = 0.65 * semantic + 0.25 * relationship + 0.10 * attribute`

- Semantic: cosine similarity of one `all-MiniLM-L6-v2` embedding per entity.
- Relationship: direct evolution-family, ability ownership, exact Pokemon type, or version-valid move learnability.
- Attributes: type/stat similarity for Pokemon; a deliberately modest same-type bonus for moves; none for abilities.
- The answer is forcibly rank `#1`. Equal scores are broken deterministically, so every eligible entity has one unique rank.

`data/` and `reports/` are generated locally and intentionally ignored by Git.

## Run

```powershell
cd benchmark
python -m pip install -r requirements.txt
python build_dataset.py
python run_benchmark.py
python run_large_scale_report.py
```

The first command that builds data downloads PokéAPI source records and caches each response under `data/raw/`. The first benchmark run downloads the open-source embedding model once and keeps it in the standard local model cache.

`run_large_scale_report.py` evaluates every eligible Pokémon answer and writes an aggregate diagnostic report with direct-relationship rank distributions and diverse sample rankings.

The current experiment uses a rarity-adjusted learnset score: broadly learnable moves retain a moderate relationship bonus, while moves learned by few eligible Pokémon keep a larger bonus. This prevents generic learnsets from overwhelming the ranking without making ordinary valid moves useless.

It also normalizes by the answer Pokémon's learnset breadth: a Pokémon that can learn hundreds of moves does not give every move the same relationship strength as a Pokémon with a short, distinctive learnset.
