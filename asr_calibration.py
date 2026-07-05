from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

from transcript_tools import TranscriptSegment


APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "YTCE_ASR_Calibration"
CALIBRATION_DIR = APP_DATA_DIR


CALIBRATION_SAMPLES: Dict[str, Dict[str, str]] = {
    "en": {
        "language_name": "English",
        "file_name": "asr_calibration_en.wav",
        "reference_text": (
            "English ASR test. "
            "Names: Kingman, ZoneX, Shadowsmith, Nicolas Cage, Caltheris, and Nyxara. "
            "I have cleared the Nicolas Cage event. "
            "We need more Caltheris content."
        ),
    },
}


def normalise_language_code(language: str | None) -> str:
    """Normalize app/ASR language to a calibration language key."""
    value = (language or "en").strip().lower()

    if not value or value in {"auto", "auto-detect"}:
        return "en"

    value = value.replace("_", "-").split("-", 1)[0]

    if value in CALIBRATION_SAMPLES:
        return value

    return "en"


def _powershell_escape(value: str) -> str:
    return value.replace("'", "''")


def _synthesise_windows_sapi(text: str, output_path: Path) -> None:
    """Create a WAV test sample using Windows .NET speech synthesis."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path.unlink(missing_ok=True)
    except Exception:
        pass

    with tempfile.TemporaryDirectory(prefix="ytce_asr_calibration_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        text_path = tmp_path / "speech_text.txt"
        script_path = tmp_path / "synth_speech.ps1"
        temp_wav_path = tmp_path / "calibration_temp.wav"

        text_path.write_text(text, encoding="utf-8")

        script_path.write_text(
            r"""
param(
    [Parameter(Mandatory=$true)][string]$TextPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Speech

$text = Get-Content -LiteralPath $TextPath -Raw

$outputDirectory = Split-Path -Parent $OutputPath

if (!(Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

if (Test-Path -LiteralPath $OutputPath) {
    Remove-Item -LiteralPath $OutputPath -Force
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

try {
    $synth.Rate = 0
    $synth.Volume = 100
    $synth.SetOutputToWaveFile($OutputPath)
    [void]$synth.Speak($text)
    $synth.SetOutputToNull()
}
finally {
    $synth.Dispose()
}
""",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-TextPath",
                str(text_path),
                "-OutputPath",
                str(temp_wav_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0 or not temp_wav_path.exists() or temp_wav_path.stat().st_size <= 0:
            error_text = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                "Could not create ASR calibration WAV with Windows speech synthesis."
                + (f"\n\n{error_text}" if error_text else "")
            )

        output_path.write_bytes(temp_wav_path.read_bytes())

    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError("ASR calibration WAV was not created.")

def ensure_asr_calibration_sample(language: str | None = None) -> Dict[str, str]:
    """Ensure the local calibration WAV/reference exists and return metadata."""
    language_code = normalise_language_code(language)
    sample = CALIBRATION_SAMPLES[language_code]

    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)

    audio_path = CALIBRATION_DIR / sample["file_name"]
    reference_path = CALIBRATION_DIR / f"asr_calibration_{language_code}.txt"

    reference_text = sample["reference_text"]

    if not reference_path.exists() or reference_path.read_text(encoding="utf-8", errors="replace").strip() != reference_text:
        reference_path.write_text(reference_text + "\n", encoding="utf-8")

    if not audio_path.exists() or audio_path.stat().st_size <= 0:
        _synthesise_windows_sapi(reference_text, audio_path)

    if not audio_path.exists() or audio_path.stat().st_size <= 0:
        raise RuntimeError(f"ASR calibration WAV was not created: {audio_path}")

    return {
        "language_code": language_code,
        "language_name": sample["language_name"],
        "audio_path": str(audio_path),
        "reference_path": str(reference_path),
        "reference_text": reference_text,
    }


def get_asr_calibration_reference_segments(language: str | None = None) -> List[TranscriptSegment]:
    """Return reference transcript segments for the calibration sample."""
    language_code = normalise_language_code(language)
    reference_text = CALIBRATION_SAMPLES[language_code]["reference_text"]

    return [
        TranscriptSegment(
            speaker="Reference",
            start="00:00:00.000",
            end="00:00:15.000",
            text=reference_text,
        )
    ]
