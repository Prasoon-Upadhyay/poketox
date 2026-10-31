# Daily Poketexto benchmark

This is the deliberately simple ranking benchmark for PokeTox. It ranks every eligible Pokemon, move, ability, and type for a small set of mystery Pokemon using only direct, explainable facts.

## Rules under test

`score = relationship + attribute`

- Relationship: direct evolution-family, ability ownership, exact Pokemon type, or version-valid move learnability.
- Attributes: shared Pokemon types and a small same-type stat tie-breaker.
- No embeddings, entity-name similarity, prose similarity, or generation bonus are used.
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

The first command that builds data downloads PokéAPI source records and caches each response under `data/raw/`.

`run_large_scale_report.py` evaluates every eligible Pokémon answer and writes an aggregate diagnostic report with direct-relationship rank distributions and diverse sample rankings.

The benchmark uses a rarity-adjusted learnset score: broadly learnable moves retain a modest relationship bonus, while moves learned by few eligible Pokémon keep a larger bonus. This prevents generic learnsets from overwhelming the ranking without making ordinary valid moves useless.

It also normalizes by the answer Pokémon's learnset breadth: a Pokémon that can learn hundreds of moves does not give every move the same relationship strength as a Pokémon with a short, distinctive learnset.

Every non-zero result carries a player-readable reason, such as `same evolution family`, `shares Rock and Ground`, `ability of target`, or `same-type learned move; rarity-adjusted`. Off-type learned moves remain valid but are deliberately distant hints.

## Test API

Run a local test server with one random Gen 1-5 target selected at startup:

```powershell
python benchmark/test_api.py
```

- `GET /api/test/target` reveals the selected target for testing only.
- `POST /api/guess` accepts a selected entity such as `{"id":"move:psychic","category":"move","name":"Psychic"}` and returns its integer rank and reason. The server uses `id` as the authoritative identity; `category` and `name` are display metadata. `{"guess":"Onix"}` remains available for manual testing, with `category` used to resolve ambiguous names.
