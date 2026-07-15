"""Local ASR default settings storage."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict


DEFAULT_ASR_SETTINGS: Dict[str, str] = {
    "engine": "faster_whisper",
    "profile_name": "Custom",
    "model_name": "small",
    "speaker_name": "Speaker 1",
    "language": "en",
    "initial_prompt": "",
    "device": "cpu",
    "compute_type": "int8",
}


def get_asr_defaults_path() -> Path:
    """Return the ASR defaults file path in the user's AppData folder."""
    appdata = os.getenv("APPDATA")

    if appdata:
        base_dir = Path(appdata) / "Modified YouTube Comment Extractor"
    else:
        base_dir = Path.home() / ".modified_youtube_comment_extractor"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "asr_defaults.json"


def load_asr_defaults() -> Dict[str, str]:
    """Load saved Local ASR defaults."""
    path = get_asr_defaults_path()

    if not path.exists():
        return dict(DEFAULT_ASR_SETTINGS)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_ASR_SETTINGS)

    defaults = dict(DEFAULT_ASR_SETTINGS)

    if isinstance(data, dict):
        for key in DEFAULT_ASR_SETTINGS:
            value = data.get(key)

            if value is not None:
                defaults[key] = str(value)

    return defaults


def save_asr_defaults(
    model_name: str,
    speaker_name: str,
    language: str,
    initial_prompt: str,
    device: str = "cpu",
    compute_type: str = "int8",
    engine: str = "faster_whisper",
    profile_name: str = "Custom",
) -> None:
    """Save Local ASR defaults for the next run."""
    settings = {
        "engine": engine or DEFAULT_ASR_SETTINGS["engine"],
        "profile_name": profile_name or DEFAULT_ASR_SETTINGS["profile_name"],
        "model_name": model_name or DEFAULT_ASR_SETTINGS["model_name"],
        "speaker_name": speaker_name or DEFAULT_ASR_SETTINGS["speaker_name"],
        "language": language or "",
        "initial_prompt": initial_prompt or "",
        "device": device or DEFAULT_ASR_SETTINGS["device"],
        "compute_type": compute_type or DEFAULT_ASR_SETTINGS["compute_type"],
    }

    path = get_asr_defaults_path()
    path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
