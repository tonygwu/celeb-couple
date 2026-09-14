"""A cap that halts, and reports the halt as a halt.

The run does not degrade at the cap, does not retry past it, and does not fall
back to a different billing route.  It stops and says what was left undone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Budget", "BudgetExhausted"]


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class Budget:
    max_calls: int
    max_fetches: int = 10**9
    calls_made: int = 0
    fetches_made: int = 0
    halted: bool = False
    halt_reason: str | None = None
    remaining_work: list[str] = field(default_factory=list)

    def spend_call(self, label: str) -> None:
        if self.calls_made >= self.max_calls:
            self.halted = True
            self.halt_reason = (
                f"budget_cap_reached: {self.calls_made} of {self.max_calls} model "
                f"calls used; stopped before {label}"
            )
            raise BudgetExhausted(self.halt_reason)
        self.calls_made += 1

    def spend_fetch(self, url: str) -> None:
        if self.fetches_made >= self.max_fetches:
            self.halted = True
            self.halt_reason = (
                f"budget_cap_reached: {self.fetches_made} of {self.max_fetches} "
                f"fetches used; stopped before {url}"
            )
            raise BudgetExhausted(self.halt_reason)
        self.fetches_made += 1

    def report(self) -> dict:
        return {
            "max_calls": self.max_calls,
            "calls_made": self.calls_made,
            "max_fetches": self.max_fetches,
            "fetches_made": self.fetches_made,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "remaining_work": list(self.remaining_work),
        }
