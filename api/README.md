# PokeTox API

FastAPI service for the first Daily Poketexto application release. It uses the accepted V6 structured-facts ranker only; the rejected V7 embedding experiments are not imported or used.

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

This is a staging API. Its active generation array is `TEST_GENERATIONS = [1, 2, 3, 4, 5]` in `poketox_api/service.py`. Each start and `POST /api/v1/daily/reset` select a random eligible Pokémon and calculate its rankings locally.

## Endpoints

- `GET /health` — service and ranker profile.
- `GET /api/v1/daily` — public puzzle metadata; never reveals the answer.
- `POST /api/v1/daily/reset` — start a new random staging game.
- `POST /api/v1/daily/give-up` — explicitly reveal the daily answer.
- `GET /api/v1/entities/suggestions?q=psy` — canonical selectable entities.
- `POST /api/v1/daily/guesses` — submit the selected entity.

See [the endpoint reference](docs/endpoints.md) or a running service's `/docs` page for request and response schemas.

Submit the canonical object returned by suggestions:

```json
{
  "id": "move:psychic",
  "category": "move",
  "name": "psychic"
}
```

`id` is authoritative. If supplied display `category` or `name` disagrees with it, the API rejects the request rather than silently accepting a mismatched entity.
