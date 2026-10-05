"""Command line entry point: `golden-eval run`."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import cast

from golden_eval.agents.base import AgentFactory
from golden_eval.report import render_text, to_json
from golden_eval.runner import run_all
from golden_eval.scenario import load_scenarios

BUILTIN_AGENTS = {
    "reference": "golden_eval.agents.reference:create",
    "broken": "golden_eval.agents.broken:create",
}


def load_factory(spec: str) -> AgentFactory:
    """Accept a built-in name or a `package.module:callable` path."""
    module_name, _, attr = BUILTIN_AGENTS.get(spec, spec).partition(":")
    if not attr:
        raise SystemExit(f"Agent must be a built-in name or 'module:callable', got {spec!r}")
    return cast(AgentFactory, getattr(importlib.import_module(module_name), attr))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="golden-eval")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run the golden set against an agent")
    run.add_argument("--agent", default="reference", help="reference, broken or module:callable")
    run.add_argument("--scenarios", type=Path, default=Path("scenarios"))
    run.add_argument("--json", type=Path, help="Also write a JSON report to this path")
    run.add_argument("-v", "--verbose", action="store_true", help="Print every transcript")
    args = parser.parse_args(argv)

    results = run_all(load_scenarios(args.scenarios), load_factory(args.agent))
    print(render_text(results, verbose=args.verbose))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(to_json(results), encoding="utf-8")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
