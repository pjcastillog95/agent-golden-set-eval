"""CLP formatting and parsing, Chilean style: $1.234.567."""

from __future__ import annotations

import re

_AMOUNT = re.compile(r"\$\s?(\d{1,3}(?:\.\d{3})+|\d+)")


def format_clp(amount: int) -> str:
    return "$" + f"{amount:,}".replace(",", ".")


def find_amounts(text: str) -> list[int]:
    """Every peso amount written as $N in the text."""
    return [int(m.replace(".", "")) for m in _AMOUNT.findall(text)]
