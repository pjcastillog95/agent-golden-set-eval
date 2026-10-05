"""A deterministic reference agent.

It stands in for an LLM agent so the golden set can run in CI without API keys.
Slot extraction is deliberately simple keyword matching on Spanish input; the
point is the contract with the tools, not language understanding.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from golden_eval.agents.base import CallContext, Message
from golden_eval.domain.money import format_clp
from golden_eval.toolbox import ToolBox

PRODUCT_LABELS = {
    "dry_20": "contenedor estándar de 20 pies",
    "dry_40": "contenedor estándar de 40 pies",
    "hc_40": "contenedor high cube de 40 pies",
    "office_20": "contenedor oficina de 20 pies",
    "reefer_20": "contenedor refrigerado de 20 pies",
}

_WORD_NUMBERS = {
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "doce": 12,
}
_NUM = r"(\d+|" + "|".join(_WORD_NUMBERS) + r")"

_MONTHS = re.compile(_NUM + r"\s+mes(?:es)?\b")
_KM = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:km|kil[oó]metros)\b")
_QTY = re.compile(_NUM + r"\s+(?:contenedores|unidades)\b")
_FEET = re.compile(r"(\d+)\s*pies\b")
_DISCOUNT = re.compile(r"descuento|rebaja|mejor precio|m[aá]s barato|negociar")


def _to_int(token: str) -> int:
    return _WORD_NUMBERS[token] if token in _WORD_NUMBERS else int(token)


def _detect_product(text: str) -> str | None:
    """Return a product id, "unknown" for an unsupported size, or None if not mentioned."""
    if "oficina" in text:
        return "office_20"
    if "refriger" in text:
        return "reefer_20"
    if "high cube" in text or re.search(r"\bhc\b", text):
        return "hc_40"
    feet = _FEET.search(text)
    if feet:
        return {"20": "dry_20", "40": "dry_40"}.get(feet.group(1), "unknown")
    return None


class ReferenceAgent:
    def __init__(self, context: CallContext) -> None:
        self.context = context
        self.customer: dict[str, Any] | None = None
        self.handed_off = False
        self.last_quote_args: dict[str, Any] | None = None

    # -- conversation ---------------------------------------------------------

    def respond(self, history: Sequence[Message], tools: ToolBox) -> str:
        if self.handed_off:
            return "Un ejecutivo ya tiene su caso y lo contactará a la brevedad."

        greeting = ""
        if self.customer is None:
            self.customer = tools.lookup_customer(self.context.caller_phone)
            if self.customer.get("status") == "credit_hold":
                return self._handoff(
                    tools, "credit_hold", "Cliente con cuenta en revisión solicita cotización."
                )
            if self.customer["found"]:
                greeting = f"Hola, {self.customer['name']}. "
            else:
                greeting = "Hola, bienvenido a Andes Box Rentals. "

        user_turns = [m.text.lower() for m in history if m.role == "user"]
        latest = user_turns[-1]

        if _DISCOUNT.search(latest):
            return greeting + self._handoff(
                tools, "discount_request", "El cliente pide condiciones comerciales especiales."
            )

        slots = self._extract(user_turns)
        if slots["product_id"] == "unknown":
            return greeting + (
                "No arrendamos ese tamaño. Tenemos contenedores estándar de 20 y 40 pies, "
                "high cube de 40 pies, oficina de 20 pies y refrigerado de 20 pies."
            )
        if slots["product_id"] is None:
            return greeting + "¿Qué tipo de contenedor necesita?"
        if slots["months"] is None:
            return greeting + "¿Por cuántos meses lo necesita?"
        if slots["distance_km"] is None:
            return greeting + "¿A cuántos kilómetros de Santiago queda la obra o bodega?"

        if slots == self.last_quote_args:
            return greeting + "¿Hay algo más en lo que pueda ayudarle?"
        self.last_quote_args = slots
        result = tools.quote(**slots)
        if not result["ok"]:
            return greeting + self._handoff(
                tools, result["error"], "Solicitud fuera de lo que se cotiza automáticamente."
            )
        return greeting + self._quote_reply(result)

    # -- helpers --------------------------------------------------------------

    def _extract(self, user_turns: Sequence[str]) -> dict[str, Any]:
        slots: dict[str, Any] = {
            "product_id": None,
            "quantity": 1,
            "months": None,
            "distance_km": None,
        }
        for text in user_turns:  # later turns override earlier ones
            if (product := _detect_product(text)) is not None:
                slots["product_id"] = product
            if m := _MONTHS.search(text):
                slots["months"] = _to_int(m.group(1))
            if m := _KM.search(text):
                km = float(m.group(1).replace(",", "."))
                slots["distance_km"] = int(km) if km.is_integer() else km
            if m := _QTY.search(text):
                slots["quantity"] = _to_int(m.group(1))
        return slots

    def _quote_reply(self, q: dict[str, Any]) -> str:
        label = PRODUCT_LABELS[q["product_id"]]
        reply = (
            f"Para {q['quantity']} {label} por {q['billed_months']} meses, "
            f"a {q['distance_km']} km: arriendo {format_clp(q['rental'])}, "
            f"flete de entrega y retiro {format_clp(q['freight'])}, "
            f"neto {format_clp(q['net'])}, IVA {format_clp(q['vat'])}. "
            f"Total {format_clp(q['total'])}."
        )
        if q["minimum_applied"]:
            reply += (
                f" El arriendo mínimo para este contenedor es de {q['billed_months']} meses, "
                f"por eso no se cotizan {q['requested_months']}."
            )
        return reply

    def _handoff(self, tools: ToolBox, reason: str, summary: str) -> str:
        tools.request_handoff(reason, summary)
        self.handed_off = True
        return "Voy a derivar su solicitud a un ejecutivo, que lo contactará hoy mismo."


def create(context: CallContext) -> ReferenceAgent:
    return ReferenceAgent(context)
