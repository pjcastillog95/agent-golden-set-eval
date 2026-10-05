"""Run every scenario against an agent and collect pass/fail results."""

from __future__ import annotations

from dataclasses import dataclass

from golden_eval.agents.base import AgentFactory, CallContext, Message
from golden_eval.checks import CheckResult, Transcript, run_checks
from golden_eval.scenario import Scenario
from golden_eval.toolbox import ToolBox


@dataclass(frozen=True)
class ScenarioResult:
    scenario: Scenario
    transcript: Transcript
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


def run_scenario(scenario: Scenario, factory: AgentFactory) -> ScenarioResult:
    agent = factory(CallContext(caller_phone=scenario.caller_phone))
    tools = ToolBox()
    messages: list[Message] = []
    for turn, text in enumerate(scenario.turns):
        tools.turn = turn
        messages.append(Message("user", text))
        messages.append(Message("agent", agent.respond(list(messages), tools)))
    transcript = Transcript(messages=messages, calls=list(tools.calls))
    return ScenarioResult(scenario, transcript, run_checks(transcript, scenario.expected))


def run_all(scenarios: list[Scenario], factory: AgentFactory) -> list[ScenarioResult]:
    return [run_scenario(s, factory) for s in scenarios]
