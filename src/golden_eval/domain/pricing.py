"""Deterministic pricing: catalog, minimum rental terms and freight by distance.

Every number a customer hears must come from here, never from the language model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    monthly_rate: int
    min_months: int


@dataclass(frozen=True)
class Quote:
    product_id: str
    quantity: int
    requested_months: int
    billed_months: int
    minimum_applied: bool
    distance_km: float
    rental: int
    freight: int
    net: int
    vat: int
    total: int


class QuoteError(ValueError):
    """Raised when a request cannot be quoted automatically."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        files("golden_eval.domain").joinpath("data", name).read_text(encoding="utf-8")
    )
    return data


@cache
def _catalog() -> dict[str, Any]:
    return _load("catalog.json")


@cache
def _freight() -> dict[str, Any]:
    return _load("freight.json")


def list_products() -> list[Product]:
    return [Product(**p) for p in _catalog()["products"]]


def get_product(product_id: str) -> Product:
    for product in list_products():
        if product.id == product_id:
            return product
    raise QuoteError("unknown_product", f"Unknown product: {product_id}")


def freight_per_leg(distance_km: float) -> int:
    """Freight for one container and one leg. Raises QuoteError beyond the last band."""
    if distance_km < 0:
        raise QuoteError("invalid_distance", "Distance cannot be negative")
    for band in _freight()["bands"]:
        if distance_km <= band["max_km"]:
            extra = 0
            if "per_km_over" in band:
                extra = round((distance_km - band["over_km"]) * band["per_km_over"])
            return int(band["flat"] + extra)
    raise QuoteError("distance_out_of_range", "Distance requires a manual logistics quote")


def quote(product_id: str, quantity: int, months: int, distance_km: float) -> Quote:
    catalog = _catalog()
    product = get_product(product_id)
    if quantity < 1 or months < 1:
        raise QuoteError("invalid_request", "Quantity and months must be at least 1")
    if quantity > catalog["max_containers_per_quote"]:
        raise QuoteError("volume_over_limit", "Volume orders are quoted by a sales executive")

    billed_months = max(months, product.min_months)
    rental = quantity * product.monthly_rate * billed_months
    freight = quantity * freight_per_leg(distance_km) * _freight()["legs_per_rental"]
    net = rental + freight
    vat = round(net * catalog["vat_rate"])
    return Quote(
        product_id=product.id,
        quantity=quantity,
        requested_months=months,
        billed_months=billed_months,
        minimum_applied=billed_months > months,
        distance_km=distance_km,
        rental=rental,
        freight=freight,
        net=net,
        vat=vat,
        total=net + vat,
    )
