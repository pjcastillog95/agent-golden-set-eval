"""The interface an agent must implement to be evaluated."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from golden_eval.toolbox import ToolBox


@dataclass(frozen=True)
class Message:
    role: Literal["user", "agent"]
    text: str


@dataclass(frozen=True)
class CallContext:
    """Metadata the telephony or messaging channel provides before the first turn."""

    caller_phone: str


class Agent(Protocol):
    def respond(self, history: Sequence[Message], tools: ToolBox) -> str:
        """Return the agent's next reply. Side effects go through `tools`."""
        ...


AgentFactory = Callable[[CallContext], Agent]
