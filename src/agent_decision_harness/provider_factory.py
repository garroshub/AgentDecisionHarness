from __future__ import annotations

from .claude_code_provider import ClaudeCodeProvider
from .codex_provider import CodexCLIProvider

_PROVIDERS = {"codex", "claude"}


def normalize_provider_name(name: str) -> str:
    normalized = name.strip().lower()
    if normalized not in _PROVIDERS:
        raise ValueError(
            f"unsupported provider {name!r}; expected codex or claude"
        )
    return normalized


def create_provider(
    *,
    provider: str,
    model: str,
    effort: str = "high",
    executable: str | None = None,
    timeout_seconds: int = 240,
):
    normalized = normalize_provider_name(provider)
    if normalized == "codex":
        return CodexCLIProvider(
            model=model,
            effort=effort,
            codex_bin=executable,
            timeout_seconds=timeout_seconds,
        )
    return ClaudeCodeProvider(
        model=model,
        effort=effort,
        claude_bin=executable,
        timeout_seconds=timeout_seconds,
    )
