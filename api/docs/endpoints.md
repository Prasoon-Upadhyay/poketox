# PokeTox API endpoint reference

Interactive OpenAPI documentation is available from a running service at `/docs`.

## `POST /api/v1/daily/start`

Starts a random game from the selected generations and builds its in-memory rank table.

```json
{ "generations": [1, 2, 3, 4, 5] }
```

`generations` must contain at least one unique number from `1` to `9`.

Response `200`:

```json
{
  "puzzle_id": "staging-5f0a620629a9",
  "generations": [1, 2, 3, 4, 5],
  "categories": ["pokemon", "move", "ability", "type"]
}
```

## `GET /api/v1/daily`

Returns public metadata for the active game. It never returns the hidden answer. Start a game first.

## `POST /api/v1/daily/reset`

Uses the same generation-selection body as `/start`, chooses a new random eligible target, and returns fresh public metadata. The frontend should clear its guess history after this response.

## `GET /api/v1/entities/suggestions`

Searches selectable entities for autocomplete. `q` is required (1–80 characters); `limit` is optional (1–20, default 10). Submit the returned canonical object rather than free text.

## `POST /api/v1/daily/guesses`

Submits one selected entity. `id` is authoritative; supplied `category` and `name` must match it. The response contains a deterministic rank and `solved` status. Duplicate guesses are rejected with `409`.

## `POST /api/v1/daily/give-up`

Explicitly gives up and reveals the current target. It is a `POST` action so a browser prefetch or cache cannot reveal it accidentally.
