from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from .provider_common import (
    EXPECTED_CANDIDATE_KEYS,
    build_candidate_prompt,
    build_candidate_schema,
    loads_strict,
    record_from_candidate_mapping,
)
from .records import ForecastRecord
from .task_spec import DEFAULT_TASK, TaskSpec


def _candidate_from_envelope(
    text: str,
) -> dict[str, Any]:
    outer = loads_strict(text)
    if not isinstance(outer, dict):
        raise ValueError(
            "Claude Code output must be a JSON object"
        )

    if set(outer) == EXPECTED_CANDIDATE_KEYS:
        return outer

    for key in (
        "structured_output",
        "structuredOutput",
    ):
        value = outer.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            parsed = loads_strict(value)
            if isinstance(parsed, dict):
                return parsed

    value = outer.get("result")
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = loads_strict(value)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError(
        "Claude Code output did not contain a candidate"
    )


def parse_claude_candidate_output(
    text: str,
    *,
    case_id: str,
    evidence_text: str,
    model: str,
    draw_index: int,
    task: TaskSpec = DEFAULT_TASK,
) -> ForecastRecord:
    return record_from_candidate_mapping(
        _candidate_from_envelope(text),
        case_id=case_id,
        evidence_text=evidence_text,
        model=model,
        source="claude_code_live",
        draw_index=draw_index,
        provider_label="Claude",
        task=task,
    )


def _resolve_claude_prefix(
    claude_bin: str | None = None,
) -> list[str]:
    if claude_bin:
        located = (
            shutil.which(claude_bin)
            or claude_bin
        )
    else:
        located = (
            shutil.which("claude.exe")
            or shutil.which("claude.cmd")
            or shutil.which("claude")
        )
        if not located:
            appdata = os.environ.get("APPDATA")
            if appdata:
                for name in (
                    "claude.exe",
                    "claude.cmd",
                ):
                    fallback = (
                        Path(appdata)
                        / "npm"
                        / name
                    )
                    if fallback.is_file():
                        located = str(fallback)
                        break

    if not located:
        raise RuntimeError(
            "cannot find Claude Code CLI; pass --executable"
        )

    launcher = Path(located).expanduser().resolve()
    if launcher.suffix.lower() == ".exe":
        return [str(launcher)]

    if launcher.suffix.lower() == ".js":
        entrypoint = launcher
    else:
        package_root = (
            launcher.parent
            / "node_modules"
            / "@anthropic-ai"
            / "claude-code"
        )
        candidates = [
            package_root / "cli.js",
            package_root / "dist" / "cli.js",
        ]
        entrypoint = next(
            (
                path.resolve()
                for path in candidates
                if path.is_file()
            ),
            None,
        )

    if entrypoint is not None:
        node = (
            shutil.which("node.exe")
            or shutil.which("node")
        )
        if not node:
            raise RuntimeError("Node.js is required")
        return [node, str(entrypoint)]

    if launcher.suffix.lower() in {
        ".cmd",
        ".bat",
    }:
        return [
            "cmd.exe",
            "/d",
            "/s",
            "/c",
            str(launcher),
        ]

    return [str(launcher)]


class ClaudeCodeProvider:
    provider_name = "claude"

    def __init__(
        self,
        *,
        model: str,
        effort: str = "high",
        claude_bin: str | None = None,
        timeout_seconds: int = 240,
    ) -> None:
        if not model.strip():
            raise ValueError("model must be non-empty")
        if effort not in {"low", "medium", "high"}:
            raise ValueError(
                "effort must be low, medium, or high"
            )
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive"
            )
        self.model = model
        self.effort = effort
        self.claude_bin = claude_bin
        self.timeout_seconds = timeout_seconds

    def _command(
        self,
        task: TaskSpec = DEFAULT_TASK,
    ) -> list[str]:
        schema = json.dumps(
            build_candidate_schema(task),
            separators=(",", ":"),
        )
        return [
            *_resolve_claude_prefix(
                self.claude_bin
            ),
            "-p",
            "--model",
            self.model,
            "--effort",
            self.effort,
            "--output-format",
            "json",
            "--json-schema",
            schema,
            "--max-turns",
            "1",
            "--no-session-persistence",
            "--safe-mode",
            "--restricted",
            "--tools",
            "",
            "--disallowedTools",
            "mcp__*",
            "--permission-prompts",
            "none",
            "--no-chrome",
            "--disable-slash-commands",
            "--system-prompt",
            (
                "Use only the supplied point-in-time "
                "packet and return the requested schema."
            ),
            "Follow the piped instructions exactly.",
        ]

    def generate(
        self,
        case_view: Mapping[str, Any],
        draw_index: int,
        task: TaskSpec = DEFAULT_TASK,
        draws: int = 3,
    ) -> ForecastRecord:
        prompt = build_candidate_prompt(
            case_view,
            draw_index,
            task,
            draws,
        )

        with tempfile.TemporaryDirectory(
            prefix="adh-claude-"
        ) as temp_dir:
            completed = subprocess.run(
                self._command(task),
                input=prompt,
                text=True,
                capture_output=True,
                cwd=Path(temp_dir),
                timeout=self.timeout_seconds,
                check=False,
            )
            if completed.returncode != 0:
                stderr = completed.stderr.strip()
                tail = (
                    stderr[-2000:]
                    if stderr
                    else "no stderr"
                )
                raise RuntimeError(
                    f"Claude draw {draw_index} failed: {tail}"
                )
            return parse_claude_candidate_output(
                completed.stdout.strip(),
                case_id=str(case_view["case_id"]),
                evidence_text=str(
                    case_view["evidence_text"]
                ),
                model=self.model,
                draw_index=draw_index,
                task=task,
            )
