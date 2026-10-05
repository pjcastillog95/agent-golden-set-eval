"""Simulated CRM backed by a local JSON file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    phone: str
    status: str


@cache
def _customers() -> tuple[Customer, ...]:
    raw = files("golden_eval.domain").joinpath("data", "crm.json").read_text(encoding="utf-8")
    return tuple(Customer(**c) for c in json.loads(raw)["customers"])


def find_by_phone(phone: str) -> Customer | None:
    for customer in _customers():
        if customer.phone == phone:
            return customer
    return None
