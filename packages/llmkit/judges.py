"""Judge adapters: one callable per model family, one telemetry shape.

Every adapter returns ``(text, telemetry)``.  Raw text is written to disk
BEFORE any parsing, so a parse failure still leaves an auditable artifact of
what the model actually said rather than what the parser extracted.

Model identity is ASSERTED from telemetry where the harness reports it, and
where it cannot be, the record says ``served_model_verified: false`` instead of
pretending.

Never invoke the judge through the ``cl`` launcher: it injects
``--dangerously-skip-permissions``, which would give a judge filesystem access
to the very corpus it is meant to be isolated from.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from packages.llmkit.taxonomy import (
    E_AUTH_QUOTA,
    E_EMPTY,
    E_MODEL_MISMATCH,
    E_TIMEOUT,
    E_TOOL_USE,
    classify_cli_failure,
)

__all__ = [
    "JudgeResult",
    "Judge",
    "FakeJudge",
    "ClaudeJudge",
    "GeminiJudge",
    "CodexJudge",
    "assert_subscription_only",
    "JudgeError",
]


class JudgeError(RuntimeError):
    def __init__(self, error_type: str, detail: str) -> None:
        super().__init__(f"{error_type}: {detail}")
        self.error_type = error_type
        self.detail = detail


@dataclass(frozen=True)
class JudgeResult:
    text: str
    telemetry: dict


class Judge(Protocol):
    name: str

    def __call__(self, prompt: str, timeout: int) -> JudgeResult: ...


def assert_subscription_only(env: dict[str, str] | None = None) -> None:
    """Refuse to run if an API key is visible to the child process.

    The operator chose subscription quota with no API billing.  That choice is
    asserted at start-up rather than merely intended, because a Claude Code
    account whose token has been rotated out shows the right org name, says
    "Not logged in", and silently falls back to API billing.
    """
    env = os.environ if env is None else env
    leaked = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if env.get(k)]
    if leaked:
        raise JudgeError(
            E_AUTH_QUOTA,
            f"{', '.join(leaked)} is set; this run is subscription-only and must "
            "not be able to fall back to API billing. Unset it and re-run.",
        )


class FakeJudge:
    """A judge that answers from a table.  Tests never touch a network."""

    def __init__(self, name: str, responder: Callable[[str], str]) -> None:
        self.name = name
        self._responder = responder
        self.calls: list[str] = []

    def __call__(self, prompt: str, timeout: int = 0) -> JudgeResult:
        self.calls.append(prompt)
        return JudgeResult(
            text=self._responder(prompt),
            telemetry={
                "harness": "fake",
                "requested_model": self.name,
                "served_model": self.name,
                "served_model_verified": True,
            },
        )


class ClaudeJudge:
    """Drives the `claude` CLI headlessly on one account's config dir."""

    def __init__(self, name: str, model: str, config_dir: str | None = None,
                 binary: str = "claude", effort: str = "high") -> None:
        if Path(binary).name == "cl":
            raise JudgeError(
                E_AUTH_QUOTA,
                "refusing to run the judge through `cl`: it injects "
                "--dangerously-skip-permissions",
            )
        self.name = name
        self.model = model
        self.config_dir = config_dir
        self.binary = binary
        self.effort = effort

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("ANTHROPIC_API_KEY", None)
        if self.config_dir:
            env["CLAUDE_CONFIG_DIR"] = self.config_dir
        else:
            env.pop("CLAUDE_CONFIG_DIR", None)  # bare `claude` targets account A
        return env

    def __call__(self, prompt: str, timeout: int = 600) -> JudgeResult:
        assert_subscription_only(self._env())
        cmd = [
            self.binary, "-p", prompt,
            "--model", self.model,
            "--output-format", "json",
            "--permission-prompts", "none",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--setting-sources", "",
            "--max-turns", "4",
        ]
        # cwd is a jail outside the repo so the judge cannot read the corpus
        with tempfile.TemporaryDirectory(prefix="celeb-judge-") as jail:
            try:
                proc = subprocess.run(
                    cmd, cwd=jail, env=self._env(), capture_output=True,
                    text=True, timeout=timeout,
                    # The CLI waits 3s for stdin and then warns on stderr; closing
                    # it makes the call deterministic instead of timing-dependent.
                    stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired as exc:
                raise JudgeError(E_TIMEOUT, f"{self.name} exceeded {timeout}s") from exc

        if proc.returncode != 0 or not proc.stdout.strip():
            raise JudgeError(
                classify_cli_failure(proc.returncode, proc.stdout, proc.stderr),
                f"{self.name} rc={proc.returncode} stderr={proc.stderr[:400]!r}",
            )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise JudgeError(E_EMPTY, f"{self.name} returned non-JSON envelope") from exc

        served, verified = self._served_model(payload)
        if verified and self.model.split("-")[1] not in served:
            raise JudgeError(
                E_MODEL_MISMATCH,
                f"asked for {self.model}, telemetry names {served!r}",
            )
        usage = payload.get("usage", {}) or {}
        return JudgeResult(
            text=payload.get("result", "") or "",
            telemetry={
                "harness": "claude-cli",
                "requested_model": self.model,
                "served_model": served,
                "served_model_verified": verified,
                "config_dir": self.config_dir or "__DEFAULT__",
                "cost_usd": payload.get("total_cost_usd"),
                "duration_ms": payload.get("duration_ms"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            },
        )

    @staticmethod
    def _served_model(payload: dict) -> tuple[str, bool]:
        mu = payload.get("modelUsage") or {}
        if isinstance(mu, dict) and mu:
            return ",".join(sorted(mu)), True
        return payload.get("model", "unreported"), False


class GeminiJudge:
    """Drives the Antigravity `agy` CLI.

    A genuinely different model family from Claude, which is the point: two
    judges from the SAME family would measure one family twice.
    """

    def __init__(self, name: str, model: str, binary: str = "agy") -> None:
        self.name = name
        self.model = model
        self.binary = binary

    def __call__(self, prompt: str, timeout: int = 600) -> JudgeResult:
        with tempfile.TemporaryDirectory(prefix="celeb-judge-") as jail:
            try:
                proc = subprocess.run(
                    [self.binary, "-p", prompt, "--model", self.model,
                     "--output-format", "json",
                     "--print-timeout", f"{max(timeout - 60, 60)}s"],
                    cwd=jail, capture_output=True, text=True, timeout=timeout,
                    stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired as exc:
                raise JudgeError(E_TIMEOUT, f"{self.name} exceeded {timeout}s") from exc
        if proc.returncode != 0 or not proc.stdout.strip():
            raise JudgeError(
                classify_cli_failure(proc.returncode, proc.stdout, proc.stderr),
                f"{self.name} rc={proc.returncode} stderr={proc.stderr[:400]!r}",
            )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise JudgeError(E_EMPTY, f"{self.name} returned non-JSON envelope") from exc
        if payload.get("status") != "SUCCESS":
            raise JudgeError(
                classify_cli_failure(1, proc.stdout, proc.stderr),
                f"{self.name} status={payload.get('status')!r}",
            )
        denied = payload.get("denied_actions") or []
        if denied and not (payload.get("response") or "").strip():
            # Measured 2026-09-14: gemini-3.8-flash-high reaches for a shell tool,
            # headless mode auto-denies it, and the turn ends with an empty
            # response after spending thinking tokens. Granting the permission is
            # not the fix -- a judge with filesystem access is not isolated from
            # the corpus it is being kept away from.
            raise JudgeError(
                E_TOOL_USE,
                f"{self.name} produced no answer after "
                f"{[d.get('display_name') for d in denied]} was denied in headless mode",
            )
        usage = payload.get("usage", {}) or {}
        return JudgeResult(
            text=payload.get("response", "") or "",
            telemetry={
                "harness": "agy",
                "requested_model": self.model,
                # The envelope names no model, so the request model is echoed and
                # the record says the identity was NOT verified rather than
                # implying a check that did not happen.
                "served_model": self.model,
                "served_model_verified": False,
                "duration_ms": int(payload.get("duration_seconds", 0) * 1000),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "thinking_tokens": usage.get("thinking_tokens"),
            },
        )


class CodexJudge:
    """Drives `codex exec --json`.

    Identity caveat, recorded rather than papered over: the JSONL event stream
    names no model anywhere, so ``served_model`` can only echo the request and
    ``served_model_verified`` is false.  The one identity-adjacent assertion
    available is that a reasoning effort actually took effect, which shows up as
    a non-zero ``reasoning_output_tokens`` in the turn usage.  When effort was
    requested and that count is zero, the request was not served as asked.
    """

    def __init__(self, name: str, model: str, binary: str = "codex",
                 effort: str = "high") -> None:
        self.name = name
        self.model = model
        self.binary = binary
        self.effort = effort

    def __call__(self, prompt: str, timeout: int = 900) -> JudgeResult:
        assert_subscription_only()
        cmd = [
            self.binary, "exec", "--json",
            "-m", self.model,
            "-c", f'model_reasoning_effort="{self.effort}"',
            "-s", "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "--ignore-user-config",   # no MCP servers, no project rules
            prompt,
        ]
        with tempfile.TemporaryDirectory(prefix="celeb-judge-") as jail:
            try:
                proc = subprocess.run(
                    cmd, cwd=jail, capture_output=True, text=True,
                    timeout=timeout, stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired as exc:
                raise JudgeError(E_TIMEOUT, f"{self.name} exceeded {timeout}s") from exc

        message, usage = "", {}
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "item.completed":
                item = ev.get("item") or {}
                if item.get("type") == "agent_message":
                    message = item.get("text", "") or message
            elif ev.get("type") == "turn.completed":
                usage = ev.get("usage") or {}

        if proc.returncode != 0 and not message:
            raise JudgeError(
                classify_cli_failure(proc.returncode, proc.stdout, proc.stderr),
                f"{self.name} rc={proc.returncode} stderr={proc.stderr[:400]!r}",
            )
        if not message:
            raise JudgeError(E_EMPTY, f"{self.name} produced no agent message")

        reasoning = usage.get("reasoning_output_tokens")
        # reasoning_output_tokens is RECORDED, never fatal.
        #
        # Measured 2026-09-14, twice. First an empty dossier reported zero,
        # because there is nothing to reason about, and raising discarded two
        # correct "unscored" answers. Then seven substantial turns of 234-257
        # output tokens also reported zero, while an earlier identical-shaped
        # probe reported 27. So this field does not reliably distinguish "effort
        # did not take effect" from "this turn needed little reasoning", and a
        # threshold on output length does not rescue it.
        #
        # Throwing away a valid answer over a telemetry field that cannot be
        # interpreted confidently is worse than carrying the uncertainty. The
        # flag travels with the record and the run summary counts it.
        effort_took_effect = bool(reasoning)

        return JudgeResult(
            text=message,
            telemetry={
                "harness": "codex-cli",
                "requested_model": self.model,
                "served_model": self.model,
                "served_model_verified": False,   # the stream names no model
                "effort": self.effort,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "reasoning_output_tokens": reasoning,
                "effort_took_effect": effort_took_effect,
            },
        )
