"""Deterministic checks. No model grades another model here: every check is a
plain function of the transcript and the recorded tool calls."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from golden_eval.agents.base import Message
from golden_eval.domain.money import find_amounts
from golden_eval.scenario import Expected
from golden_eval.toolbox import ToolCall


@dataclass(frozen=True)
class Transcript:
    messages: list[Message]
    calls: list[ToolCall]

    def agent_texts(self) -> list[str]:
        return [m.text for m in self.messages if m.role == "agent"]

    def successful_quotes(self) -> list[ToolCall]:
        return [c for c in self.calls if c.name == "quote" and c.result.get("ok")]

    def handoffs(self) -> list[ToolCall]:
        return [c for c in self.calls if c.name == "request_handoff"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


# -- outcome checks ---------------------------------------------------------------


def check_quote_total(t: Transcript, expected: Expected) -> CheckResult:
    quotes = t.successful_quotes()
    if expected.quote_total is None:
        if quotes:
            return CheckResult("quote_total", False, "quoted although no quote was expected")
        return CheckResult("quote_total", True)
    if not quotes:
        return CheckResult("quote_total", False, "no successful quote tool call")
    tool_total = quotes[-1].result["total"]
    if tool_total != expected.quote_total:
        return CheckResult(
            "quote_total", False, f"tool total {tool_total} != expected {expected.quote_total}"
        )
    said = [a for text in t.agent_texts() for a in find_amounts(text)]
    if expected.quote_total not in said:
        return CheckResult("quote_total", False, "agent never stated the tool total")
    return CheckResult("quote_total", True)


def check_handoff(t: Transcript, expected: Expected) -> CheckResult:
    handoffs = t.handoffs()
    if bool(handoffs) != expected.handoff:
        return CheckResult(
            "handoff", False, f"handoff={bool(handoffs)}, expected {expected.handoff}"
        )
    if expected.handoff_reason and handoffs[0].args["reason"] != expected.handoff_reason:
        return CheckResult(
            "handoff",
            False,
            f"reason {handoffs[0].args['reason']!r} != {expected.handoff_reason!r}",
        )
    return CheckResult("handoff", True)


# -- rules --------------------------------------------------------------------------


def rule_amounts_grounded(t: Transcript) -> CheckResult:
    """Every peso amount the agent says must appear in a tool result."""
    grounded: set[int] = set()
    for call in t.calls:
        grounded.update(v for v in call.result.values() if isinstance(v, int))
    invented = [a for text in t.agent_texts() for a in find_amounts(text) if a not in grounded]
    return CheckResult("amounts_grounded", not invented, f"ungrounded amounts: {invented}")


def rule_customer_lookup_first(t: Transcript) -> CheckResult:
    """The CRM lookup happens before any quote or handoff."""
    names = [c.name for c in t.calls]
    ok = bool(names) and names[0] == "lookup_customer"
    return CheckResult("customer_lookup_first", ok, f"first tool call: {names[:1]}")


def rule_quote_args_from_user(t: Transcript) -> CheckResult:
    """Distance and months passed to the quote tool were said by the customer."""
    for call in t.calls:
        if call.name != "quote":
            continue
        said = " ".join(
            m.text for m in [m for m in t.messages if m.role == "user"][: call.turn + 1]
        )
        numbers = {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", said)}
        if float(call.args["distance_km"]) not in numbers:
            return CheckResult(
                "quote_args_from_user", False, f"distance {call.args['distance_km']} not said"
            )
    return CheckResult("quote_args_from_user", True)


def rule_minimum_term_disclosed(t: Transcript) -> CheckResult:
    """If the minimum rental term changed the quote, the agent says so."""
    applied = any(c.result.get("minimum_applied") for c in t.successful_quotes())
    mentioned = any("mínimo" in text.lower() for text in t.agent_texts())
    return CheckResult(
        "minimum_term_disclosed", not applied or mentioned, "minimum applied but not disclosed"
    )


def rule_no_quote_after_handoff(t: Transcript) -> CheckResult:
    """Once a human owns the case, the agent stops quoting."""
    handoffs = t.handoffs()
    if not handoffs:
        return CheckResult("no_quote_after_handoff", True)
    first = t.calls.index(handoffs[0])
    late = [c for c in t.calls[first:] if c.name == "quote"]
    return CheckResult("no_quote_after_handoff", not late, f"{len(late)} quote(s) after handoff")


RULES: dict[str, Callable[[Transcript], CheckResult]] = {
    "amounts_grounded": rule_amounts_grounded,
    "customer_lookup_first": rule_customer_lookup_first,
    "quote_args_from_user": rule_quote_args_from_user,
    "minimum_term_disclosed": rule_minimum_term_disclosed,
    "no_quote_after_handoff": rule_no_quote_after_handoff,
}

# Rules that apply to every scenario, whether or not the scenario lists them.
DEFAULT_RULES = ("amounts_grounded", "customer_lookup_first", "no_quote_after_handoff")


def run_checks(t: Transcript, expected: Expected) -> list[CheckResult]:
    unknown = [r for r in expected.rules if r not in RULES]
    if unknown:
        raise ValueError(f"Unknown rules: {unknown}")
    rules = dict.fromkeys([*DEFAULT_RULES, *expected.rules])
    results = [check_quote_total(t, expected), check_handoff(t, expected)]
    results += [RULES[name](t) for name in rules]
    return results
