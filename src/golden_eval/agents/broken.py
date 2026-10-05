"""An agent with a realistic defect, used to show that the gate blocks a release.

It calls the quote tool, but then restates the total from its own arithmetic and
forgets the freight. This is the kind of error a language model makes when it is
allowed to do the math instead of repeating the tool output.
"""

from __future__ import annotations

from typing import Any

from golden_eval.agents.base import CallContext
from golden_eval.agents.reference import ReferenceAgent
from golden_eval.domain.money import format_clp
from golden_eval.domain.pricing import get_product


class BrokenAgent(ReferenceAgent):
    def _quote_reply(self, q: dict[str, Any]) -> str:
        product = get_product(q["product_id"])
        total = round(q["quantity"] * product.monthly_rate * q["billed_months"] * 1.19)
        return f"El total con IVA queda en {format_clp(total)}."


def create(context: CallContext) -> BrokenAgent:
    return BrokenAgent(context)
