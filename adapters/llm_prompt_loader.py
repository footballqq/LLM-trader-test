from __future__ import annotations

from pathlib import Path


def load_prompt(prompt_path: str) -> str:
    p = Path(prompt_path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


