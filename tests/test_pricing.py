import pytest

from golden_eval.domain import pricing
from golden_eval.domain.money import find_amounts, format_clp


@pytest.mark.parametrize(
    ("km", "expected"),
    [
        (0, 60000),
        (20, 60000),
        (20.5, 90000),
        (50, 90000),
        (100, 140000),
        (150, 195000),
        (300, 360000),
    ],
)
def test_freight_bands(km: float, expected: int) -> None:
    assert pricing.freight_per_leg(km) == expected


def test_freight_beyond_last_band_raises() -> None:
    with pytest.raises(pricing.QuoteError) as exc:
        pricing.freight_per_leg(301)
    assert exc.value.code == "distance_out_of_range"


def test_quote_applies_minimum_term() -> None:
    q = pricing.quote("office_20", quantity=1, months=1, distance_km=10)
    assert q.billed_months == 3
    assert q.minimum_applied
    assert (q.rental, q.freight, q.net, q.vat, q.total) == (630000, 120000, 750000, 142500, 892500)


def test_quote_rejects_volume_over_limit() -> None:
    with pytest.raises(pricing.QuoteError) as exc:
        pricing.quote("dry_20", quantity=11, months=1, distance_km=10)
    assert exc.value.code == "volume_over_limit"


def test_quote_rejects_unknown_product() -> None:
    with pytest.raises(pricing.QuoteError) as exc:
        pricing.quote("dry_10", quantity=1, months=1, distance_km=10)
    assert exc.value.code == "unknown_product"


def test_money_round_trip() -> None:
    assert format_clp(1856400) == "$1.856.400"
    assert find_amounts("Total $1.856.400, flete $280.000 y $500") == [1856400, 280000, 500]
