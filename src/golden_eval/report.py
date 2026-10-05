"""Plain-text and JSON reports."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from golden_eval.runner import ScenarioResult


def render_text(results: list[ScenarioResult], verbose: bool = False) -> str:
    width = max(len(r.scenario.id) for r in results)
    lines = []
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"{status}  {r.scenario.id.ljust(width)}  {r.scenario.description}")
        for failure in r.failures:
            lines.append(f"      - {failure.name}: {failure.detail}")
        if verbose or not r.passed:
            for m in r.transcript.messages:
                lines.append(f"      {m.role:>5}: {m.text}")
    passed = sum(r.passed for r in results)
    lines.append("")
    lines.append(f"{passed}/{len(results)} scenarios passed")
    lines.append("RELEASE: allowed" if passed == len(results) else "RELEASE: blocked")
    return "\n".join(lines)


def to_json(results: list[ScenarioResult]) -> str:
    payload: dict[str, Any] = {
        "passed": sum(r.passed for r in results),
        "total": len(results),
        "scenarios": [
            {
                "id": r.scenario.id,
                "passed": r.passed,
                "checks": [asdict(c) for c in r.checks],
                "messages": [asdict(m) for m in r.transcript.messages],
                "tool_calls": [asdict(c) for c in r.transcript.calls],
            }
            for r in results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
