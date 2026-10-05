from pathlib import Path

from golden_eval.cli import main

SCENARIOS = Path(__file__).parent.parent / "scenarios"


def test_reference_agent_passes_golden_set() -> None:
    assert main(["run", "--agent", "reference", "--scenarios", str(SCENARIOS)]) == 0


def test_broken_agent_is_blocked(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["run", "--agent", "broken", "--scenarios", str(SCENARIOS)]) == 1
    assert "RELEASE: blocked" in capsys.readouterr().out
