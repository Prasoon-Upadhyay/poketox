# PokeTox API

FastAPI service for Poketexto. It uses the accepted V6 structured-facts ranker only; the V7 embedding experiments are not imported or used.

## Prerequisite

Build the verified local PokeAPI dataset from the repository root:

```powershell
python benchmark/build_dataset.py
```

## Run

```powershell
python -m pip install -r api/requirements.txt
python -m uvicorn poketox_api.main:app --app-dir api --reload
```

The frontend supplies a non-empty, unique selection of generations `1` through `9` when it starts or resets a game. The API derives the eligible Pokémon and guesses from that selection, then keeps the rank table in memory.

## Endpoints

- `GET /health` — service and active ranker profile.
- `POST /api/v1/daily/start` — start a game for selected generations.
- `GET /api/v1/daily` — public puzzle metadata; never reveals the answer.
- `POST /api/v1/daily/reset` — start a new random game for selected generations.
- `POST /api/v1/daily/give-up` — explicitly reveal the target.
- `GET /api/v1/entities/suggestions?q=psy` — canonical selectable entities.
- `POST /api/v1/daily/guesses` — submit the selected entity.

See [the endpoint reference](docs/endpoints.md) or a running service's `/docs` page for request and response schemas.
