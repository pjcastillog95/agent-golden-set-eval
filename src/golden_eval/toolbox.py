"""Tools exposed to the agent. The runner owns the toolbox and records every call,
so checks are based on what the agent actually did, not on what it reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from golden_eval.domain import crm, pricing


@dataclass(frozen=True)
class ToolCall:
    turn: int
    name: str
    args: dict[str, Any]
    result: dict[str, Any]


@dataclass
class ToolBox:
    calls: list[ToolCall] = field(default_factory=list)
    turn: int = 0

    def _record(self, name: str, args: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(ToolCall(turn=self.turn, name=name, args=args, result=result))
        return result

    def lookup_customer(self, phone: str) -> dict[str, Any]:
        customer = crm.find_by_phone(phone)
        result: dict[str, Any] = {"found": customer is not None}
        if customer is not None:
            result |= {"id": customer.id, "name": customer.name, "status": customer.status}
        return self._record("lookup_customer", {"phone": phone}, result)

    def list_catalog(self) -> dict[str, Any]:
        products = [asdict(p) for p in pricing.list_products()]
        return self._record("list_catalog", {}, {"products": products})

    def quote(
        self, product_id: str, quantity: int, months: int, distance_km: float
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "product_id": product_id,
            "quantity": quantity,
            "months": months,
            "distance_km": distance_km,
        }
        try:
            result: dict[str, Any] = {"ok": True, **asdict(pricing.quote(**args))}
        except pricing.QuoteError as exc:
            result = {"ok": False, "error": exc.code, "message": str(exc)}
        return self._record("quote", args, result)

    def request_handoff(self, reason: str, summary: str) -> dict[str, Any]:
        return self._record(
            "request_handoff", {"reason": reason, "summary": summary}, {"accepted": True}
        )
