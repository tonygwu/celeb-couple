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
    """A call budget, and optionally a fetch budget.

    ``max_fetches`` defaulted to 10**9, which is not a cap, and every caller
    left it at the default. ``spend_fetch`` has never been called by anything,
    so ``fetches_made`` was structurally always zero -- and ``report()`` wrote
    BOTH numbers into every run artifact. A reader saw a cap of one billion
    beside a count of zero and could reasonably read that as "fetches were
    counted and stayed under a limit". Neither half was true.

    ``max_fetches`` is now None when there is no fetch budget, and the report
    stays silent about fetches until one exists or one is spent. The plan's
    "HTTP fetches <= 200, paced, breaker armed" is a real M0 bound that nothing
    enforces; that is filed in docs/BACKLOG.md rather than wired in overnight,
    because capping the retrieval path mid-chain is a behaviour change.
    """

    max_calls: int
    max_fetches: int | None = None
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
        """Count a fetch, and halt if a fetch budget was set and is spent.

        With no fetch budget this still COUNTS, so a caller that wires it in
        gets the telemetry before anyone has to choose a number.
        """
        if self.max_fetches is not None and self.fetches_made >= self.max_fetches:
            self.halted = True
            self.halt_reason = (
                f"budget_cap_reached: {self.fetches_made} of {self.max_fetches} "
                f"fetches used; stopped before {url}"
            )
            raise BudgetExhausted(self.halt_reason)
        self.fetches_made += 1

    def report(self) -> dict:
        out = {
            "max_calls": self.max_calls,
            "calls_made": self.calls_made,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "remaining_work": list(self.remaining_work),
        }
        # Silent unless there is something true to say. A cap nobody set and a
        # counter nobody increments are not measurements.
        if self.max_fetches is not None:
            out["max_fetches"] = self.max_fetches
        if self.max_fetches is not None or self.fetches_made:
            out["fetches_made"] = self.fetches_made
        return out
