from golden_eval.agents.base import Message
from golden_eval.checks import Transcript, run_checks
from golden_eval.scenario import Expected
from golden_eval.toolbox import ToolBox


def _transcript(agent_text: str, quote_distance: float = 15) -> Transcript:
    tools = ToolBox()
    tools.lookup_customer("+56900000101")
    tools.quote("dry_20", 1, 2, quote_distance)
    messages = [Message("user", "20 pies por 2 meses a 15 km"), Message("agent", agent_text)]
    return Transcript(messages, tools.calls)


def _failed(t: Transcript, expected: Expected) -> set[str]:
    return {c.name for c in run_checks(t, expected) if not c.passed}


EXPECTED = Expected(quote_total=368900, handoff=False, rules=["quote_args_from_user"])


def test_correct_transcript_passes() -> None:
    assert _failed(_transcript("Total $368.900."), EXPECTED) == set()


def test_invented_amount_fails_grounding_and_total() -> None:
    assert _failed(_transcript("Total $226.100."), EXPECTED) == {
        "amounts_grounded",
        "quote_total",
    }


def test_distance_not_said_by_user_fails() -> None:
    t = _transcript("Total $368.900.", quote_distance=25)
    assert "quote_args_from_user" in _failed(t, EXPECTED)


def test_unexpected_handoff_fails() -> None:
    tools = ToolBox()
    tools.lookup_customer("+56900000101")
    tools.request_handoff("discount_request", "x")
    t = Transcript([Message("user", "hola"), Message("agent", "lo derivo")], tools.calls)
    assert _failed(t, Expected(quote_total=None, handoff=False)) == {"handoff"}
