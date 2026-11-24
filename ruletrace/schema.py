from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Category = Literal["geral", "expositor", "oficineiro"]
Strategy = Literal["section", "window"]
SearchMode = Literal["lexical", "semantic", "hybrid"]
RegistrationID = Annotated[str, StringConstraints(pattern=r"^EVT-[0-9]{3}$")]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Query(InputModel):
    question: str = Field(min_length=5, max_length=1000)
    as_of: date
    category: Category | None = None
    registration_id: RegistrationID | None = None
    search: SearchMode = "hybrid"
    chunking: Strategy = "section"
    top_k: int = Field(default=4, ge=1, le=8, strict=True)


class RuleSource(InputModel):
    rule_id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    category: Category
    starts_on: date
    ends_on: date | None = None
    file: str = Field(min_length=1, max_length=120)

    @field_validator("ends_on")
    @classmethod
    def validate_interval(cls, value, info):
        if value is not None and "starts_on" in info.data and value <= info.data["starts_on"]:
            raise ValueError("end date must be after start date")
        return value


class Manifest(InputModel):
    sources: list[RuleSource] = Field(min_length=1, max_length=100)


class RetrievalHit(BaseModel):
    chunk_id: str
    rule_id: str
    version: str
    source: str
    locator: str
    content: str


class Registration(BaseModel):
    id: RegistrationID
    category: Literal["expositor", "oficineiro"]
    status: Literal["incompleta", "confirmada"]


class Draft(InputModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: str = Field(default="", max_length=1200)
    citations: list[str] = Field(default_factory=list, max_length=8)


class Answer(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    reason: str | None = None
    answer: str
    citations: list[RetrievalHit]
    registration: Registration | None = None
    generation_id: str | None = None
    timings_ms: dict[str, float] = Field(default_factory=dict)
