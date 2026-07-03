from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict


DEFAULT_ASR_SETTINGS = {
    "model_name": "small",
    "speaker_name": "Speaker 1",
    "language": "en",
    "initial_prompt": "",
}


def _settings_path() -> Path:
    """Return the ASR defaults file path in the user's AppData folder."""
    appdata = os.getenv("APPDATA")

    if appdata:
        base_dir = Path(appdata) / "YouTube Comment Extractor"
    else:
        base_dir = Path.home() / ".youtube_comment_extractor"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "asr_defaults.json"


def load_asr_defaults() -> Dict[str, str]:
    """Load saved Local ASR defaults."""
    path = _settings_path()

    if not path.exists():
        return dict(DEFAULT_ASR_SETTINGS)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_ASR_SETTINGS)

    defaults = dict(DEFAULT_ASR_SETTINGS)

    for key in defaults:
        value = data.get(key)

        if isinstance(value, str):
            defaults[key] = value

    return defaults


def save_asr_defaults(
    model_name: str,
    speaker_name: str,
    language: str,
    initial_prompt: str,
) -> None:
    """Save Local ASR defaults for the next run."""
    path = _settings_path()

    data = {
        "model_name": model_name or DEFAULT_ASR_SETTINGS["model_name"],
        "speaker_name": speaker_name or DEFAULT_ASR_SETTINGS["speaker_name"],
        "language": language or "",
        "initial_prompt": initial_prompt or "",
    }

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
