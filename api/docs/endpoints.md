# PokeTox API V1 endpoint reference

Interactive OpenAPI documentation is available from a running service at `/docs`.

## `GET /health`

Checks that the service has loaded its daily ranking.

Response `200`:

```json
{
  "status": "ok",
  "ranking_profile": "structured-facts-v6",
  "generations": [1, 2, 3, 4, 5]
}
```

## `GET /api/v1/daily`

Returns public metadata for the current daily puzzle. It never returns the hidden answer.

Response `200`:

```json
{
  "puzzle_id": "staging-5f0a620629a9",
  "generations": [1, 2, 3, 4, 5],
  "categories": ["pokemon", "move", "ability", "type"]
}
```

## `GET /api/v1/entities/suggestions`

Searches selectable entities for autocomplete.

Query parameters:

- `q` — required search text, 1–80 characters.
- `limit` — optional result count, 1–20; defaults to `10`.

Response `200`:

```json
[
  { "id": "move:psychic", "category": "move", "name": "psychic" },
  { "id": "type:psychic", "category": "type", "name": "psychic" }
]
```

The frontend should display `name` and `category`, then submit the selected object rather than free text.

## `POST /api/v1/daily/reset`

Starts a new staging game: the API chooses a different random Pokémon from its in-code generation array, rebuilds its local rank table, and returns new public metadata. The frontend should clear its guess history after this response. It does not reveal the new target.

Response `200` is the same public metadata returned by `GET /api/v1/daily`.

## `POST /api/v1/daily/give-up`

Explicitly gives up and reveals the current target. This is a `POST` action to avoid an accidental reveal caused by a browser prefetch or cache.

Response `200`:

```json
{
  "status": "given_up",
  "puzzle_id": "staging-5f0a620629a9",
  "target": { "id": "pokemon:pikachu", "category": "pokemon", "name": "pikachu" }
}
```

## `POST /api/v1/daily/guesses`

Submits one selected entity. `id` is authoritative; `category` and `name` are validated against its canonical record.

Request body:

```json
{
  "id": "move:psychic",
  "category": "move",
  "name": "psychic"
}
```

Response `200`:

```json
{
  "status": "accepted",
  "guess": { "id": "move:psychic", "category": "move", "name": "psychic" },
  "rank": 312,
  "solved": false
}
```

Response `422` is returned for malformed input, an unknown ID, an entity outside the active test generations, or mismatched display metadata:

```json
{
  "status": "rejected",
  "message": "category does not match the selected entity ID."
}
```
