from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .schemas import DailyGameResponse, ErrorResponse, GenerationSelection, GiveUpResponse, GuessResponse, Suggestion
from .service import DailyGame


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.daily_game = DailyGame()
    yield


app = FastAPI(title="PokeTox API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"status": "rejected", "message": "Request validation failed.", "errors": exc.errors()})


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"status": "rejected", "message": str(exc.detail)})


@app.get(
    "/health",
    summary="Check API health",
    description="Returns the active ranking profile and current generation set. It never exposes the daily answer.",
)
def health(request: Request) -> dict:
    """Report readiness and the active non-semantic ranking profile."""
    game: DailyGame = request.app.state.daily_game
    return {"status": "ok", "ranking_profile": "structured-facts-v6", "generations": sorted(game.generations)}


@app.get(
    "/api/v1/daily",
    response_model=DailyGameResponse,
    summary="Read public Daily Poketexto metadata",
    description="Returns the current game identifier, allowed generations, and accepted entity categories. The hidden Pokémon is never included.",
)
def daily(request: Request) -> dict:
    """Return public daily puzzle metadata without revealing the answer."""
    return request.app.state.daily_game.public_metadata()


@app.post(
    "/api/v1/daily/start",
    response_model=DailyGameResponse,
    summary="Start a Poketexto game for selected generations",
    description="Accepts the generation selection from the frontend, chooses a random eligible Pokemon, and builds that game's rank table in memory.",
)
def start_daily(request: Request, selection: GenerationSelection) -> dict:
    """Configure and start a game from the caller's selected generations."""
    game: DailyGame = request.app.state.daily_game
    game.refresh(selection.generations)
    return game.public_metadata()


@app.post(
    "/api/v1/daily/reset",
    response_model=DailyGameResponse,
    summary="Reset a client's Daily Poketexto session",
    description="Accepts a generation selection, chooses a new random eligible Pokémon, recalculates rankings, and returns public game metadata.",
)
def reset_daily(request: Request, selection: GenerationSelection) -> dict:
    """Start a fresh game with a newly selected random target."""
    game: DailyGame = request.app.state.daily_game
    game.refresh(selection.generations)
    return game.public_metadata()


@app.post(
    "/api/v1/daily/give-up",
    response_model=GiveUpResponse,
    summary="Give up and reveal the Daily Poketexto target",
    description="Explicitly reveals the current daily Pokémon. This is POST rather than GET so browsers and caches cannot reveal it accidentally.",
)
def give_up(request: Request) -> dict:
    """Reveal the target only after the player intentionally gives up."""
    return request.app.state.daily_game.reveal_target()


@app.get(
    "/api/v1/entities/suggestions",
    response_model=list[Suggestion],
    summary="Find selectable guess entities",
    description="Searches eligible Pokémon, moves, abilities, and types by normalized display name. Submit one returned object unchanged to the guess endpoint.",
)
def suggestions(request: Request, q: str = Query(min_length=1, max_length=80), limit: int = Query(default=10, ge=1, le=20)) -> list[dict]:
    """Return canonical, in-scope entities for the frontend autocomplete control."""
    return request.app.state.daily_game.suggestion_list(q, limit)


@app.post(
    "/api/v1/daily/guesses",
    response_model=GuessResponse,
    responses={422: {"model": ErrorResponse, "description": "Invalid or ineligible selected entity."}},
    summary="Submit a Daily Poketexto guess",
    description="Accepts an entity selected from suggestions. The canonical ID is authoritative; optional display category and name must match that ID. Returns a deterministic global rank and solved status.",
)
def submit_guess(request: Request, guess: Suggestion) -> dict:
    """Validate one selected entity and return its deterministic rank for today."""
    return request.app.state.daily_game.submit(guess.id, guess.category, guess.name)
