from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from .provider_common import (
    build_candidate_prompt,
    build_candidate_schema,
    loads_strict,
    record_from_candidate_mapping,
)
from .records import ForecastRecord
from .task_spec import DEFAULT_TASK, TaskSpec

DISABLED_FEATURES = (
    "apps",
    "codex_apps_mcp_2026_07_28",
    "enable_mcp_apps",
    "mcp_2026_07_28",
    "shell_tool",
    "unified_exec",
    "unified_exec_tty",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "in_app_browser",
    "computer_use",
    "plugins",
    "remote_plugin",
    "multi_agent",
    "multi_agent_v2",
    "view_image",
    "workspace_dependencies",
    "auth_elicitation",
    "standalone_web_search",
)


def parse_candidate_output(
    text: str,
    *,
    case_id: str,
    evidence_text: str,
    model: str,
    draw_index: int,
    task: TaskSpec = DEFAULT_TASK,
) -> ForecastRecord:
    raw = loads_strict(text)
    if not isinstance(raw, dict):
        raise ValueError(
            "Codex candidate output must be one JSON object"
        )
    return record_from_candidate_mapping(
        raw,
        case_id=case_id,
        evidence_text=evidence_text,
        model=model,
        source="codex_live",
        draw_index=draw_index,
        provider_label="Codex",
        task=task,
    )


def _resolve_codex_prefix(
    codex_bin: str | None = None,
) -> list[str]:
    if codex_bin:
        located = shutil.which(codex_bin) or codex_bin
    else:
        located = (
            shutil.which("codex.cmd")
            or shutil.which("codex")
        )
        if not located:
            appdata = os.environ.get("APPDATA")
            fallback = (
                Path(appdata) / "npm" / "codex.cmd"
                if appdata
                else None
            )
            if fallback and fallback.is_file():
                located = str(fallback)

    if not located:
        raise RuntimeError(
            "cannot find Codex CLI; pass --executable"
        )

    launcher = Path(located).expanduser().resolve()
    entrypoint: Path | None
    if launcher.suffix.lower() == ".js":
        entrypoint = launcher
    else:
        candidates = [
            launcher.parent
            / "node_modules"
            / "@openai"
            / "codex"
            / "bin"
            / "codex.js",
        ]
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(
                Path(appdata)
                / "npm"
                / "node_modules"
                / "@openai"
                / "codex"
                / "bin"
                / "codex.js"
            )
        entrypoint = next(
            (
                path.resolve()
                for path in candidates
                if path.is_file()
            ),
            None,
        )

    if entrypoint is None:
        if launcher.suffix.lower() == ".exe":
            return [str(launcher)]
        raise RuntimeError(
            f"cannot resolve Codex entrypoint from {launcher}"
        )

    node = (
        shutil.which("node.exe")
        or shutil.which("node")
    )
    if not node:
        raise RuntimeError("Node.js is required")
    return [node, str(entrypoint)]


class CodexCLIProvider:
    provider_name = "codex"

    def __init__(
        self,
        *,
        model: str,
        effort: str = "high",
        codex_bin: str | None = None,
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
        self.codex_bin = codex_bin
        self.timeout_seconds = timeout_seconds

    def _command(
        self,
        *,
        workspace: Path,
        schema_path: Path,
        output_path: Path,
    ) -> list[str]:
        command = [
            *_resolve_codex_prefix(self.codex_bin),
            "--no-daemon",
            "--ask-for-approval",
            "never",
            "--strict-config",
            "--config",
            f'model_reasoning_effort="{self.effort}"',
            "--config",
            'web_search="disabled"',
        ]
        for feature in DISABLED_FEATURES:
            command.extend(("--disable", feature))
        command.extend(
            (
                "exec",
                "--model",
                self.model,
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--cd",
                str(workspace),
                "--ephemeral",
                "--ignore-user-config",
                "--json",
                "--color",
                "never",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-",
            )
        )
        return command

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
            prefix="adh-codex-"
        ) as temp_dir:
            root = Path(temp_dir).resolve()
            workspace = root / "workspace"
            workspace.mkdir()
            schema_path = (
                workspace / "candidate.schema.json"
            )
            output_path = root / "last_message.json"
            schema_path.write_text(
                json.dumps(
                    build_candidate_schema(task),
                    indent=2,
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                self._command(
                    workspace=workspace,
                    schema_path=schema_path,
                    output_path=output_path,
                ),
                input=prompt,
                text=True,
                capture_output=True,
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
                    f"Codex draw {draw_index} failed: {tail}"
                )
            if not output_path.is_file():
                raise RuntimeError(
                    "Codex did not produce structured output"
                )

            return parse_candidate_output(
                output_path.read_text(
                    encoding="utf-8-sig"
                ).strip(),
                case_id=str(case_view["case_id"]),
                evidence_text=str(
                    case_view["evidence_text"]
                ),
                model=self.model,
                draw_index=draw_index,
                task=task,
            )
