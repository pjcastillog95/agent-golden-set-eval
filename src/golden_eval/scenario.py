"""Golden-set scenarios: a scripted conversation plus the expected outcome."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote_total: int | None = Field(
        description="Total in CLP, VAT included, that the customer must hear. None: no quote."
    )
    handoff: bool
    handoff_reason: str | None = None
    rules: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    caller_phone: str
    turns: list[str] = Field(min_length=1)
    expected: Expected


def load_scenarios(directory: Path) -> list[Scenario]:
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise FileNotFoundError(f"No scenarios found in {directory}")
    scenarios = [Scenario.model_validate(yaml.safe_load(p.read_text("utf-8"))) for p in paths]
    ids = [s.id for s in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("Scenario ids must be unique")
    return scenarios
