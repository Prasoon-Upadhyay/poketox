from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Category = Literal["pokemon", "move", "ability", "type"]


class EntityRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^(pokemon|move|ability|type):[a-z0-9-]+$", max_length=120)
    category: Category | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)


class Suggestion(EntityRef):
    category: Category
    name: str
    types: list[str] = Field(default_factory=list)
    move_type: str | None = None
    damage_class: Literal["physical", "special", "status"] | None = None
    power: int | None = Field(default=None, ge=0)
    sprite_id: int | None = Field(default=None, ge=1)


class GuessResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    guess: Suggestion
    rank: int = Field(ge=1)
    solved: bool


class ErrorResponse(BaseModel):
    status: Literal["rejected"] = "rejected"
    message: str


class DailyGameResponse(BaseModel):
    puzzle_id: str
    generations: list[int]
    categories: list[Category]


class GiveUpResponse(BaseModel):
    status: Literal["given_up"] = "given_up"
    puzzle_id: str
    target: Suggestion
