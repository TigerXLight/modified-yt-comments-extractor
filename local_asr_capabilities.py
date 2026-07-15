"""Local-only ASR capability wording helpers.

These helpers describe configured local ASR capability. They do not download
models, run transcription, probe providers, or contact a network service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence


ASR_DEVICE_CPU = "cpu"
ASR_DEVICE_CUDA = "cuda"
ASR_DEVICE_VULKAN = "vulkan"
ASR_ENGINE_FASTER_WHISPER = "faster_whisper"
ASR_ENGINE_WHISPERCPP_VULKAN = "whispercpp_vulkan"
ASR_BEST_TESTED_PROFILE = "Best-tested local profile"
ASR_RUNNER_FASTER_WHISPER = "asr_tools"
ASR_RUNNER_WHISPERCPP = "asr_whispercpp"
BENCHMARKED_LOCAL_ASR_ENGINE = "whisper.cpp"
BENCHMARKED_LOCAL_ASR_ACCELERATION = "Vulkan"
BENCHMARKED_LOCAL_ASR_MODEL = "large-v3"


@dataclass(frozen=True)
class LocalASRCapabilityInputs:
    """Facts gathered by the caller for local ASR status text."""

    selection: Optional["LocalASRSelection"] = None
    model_name: str = "small"
    device: str = ASR_DEVICE_CPU
    compute_type: str = "int8"
    faster_whisper_available: bool = False
    faster_whisper_error: str = ""
    cuda_available: bool = False
    cuda_device_name: str = ""
    cuda_error: str = ""
    whispercpp_vulkan_available: bool = False
    whispercpp_vulkan_binary_detected: bool = False
    whispercpp_vulkan_model_detected: bool = False
    gpu_vendor_hint: str = ""


@dataclass(frozen=True)
class LocalASRSelection:
    """Resolved Local ASR selection with engine-specific fields."""

    engine_id: str = ASR_ENGINE_FASTER_WHISPER
    profile_name: str = "Custom"
    model_name: str = "small"
    acceleration: str = ASR_DEVICE_CPU
    faster_whisper_compute_type: Optional[str] = "int8"
    resolved_runner: str = ASR_RUNNER_FASTER_WHISPER


def normalize_asr_engine(value: str) -> str:
    """Normalize saved/display ASR engine values."""
    lowered = (value or "").strip().casefold()
    if "whisper.cpp" in lowered and "vulkan" in lowered:
        return ASR_ENGINE_WHISPERCPP_VULKAN
    if lowered in {
        ASR_ENGINE_WHISPERCPP_VULKAN,
        "whispercpp",
        "whisper.cpp",
        "whisper.cpp vulkan",
        "vulkan",
        ASR_BEST_TESTED_PROFILE.casefold(),
    }:
        return ASR_ENGINE_WHISPERCPP_VULKAN
    return ASR_ENGINE_FASTER_WHISPER


def resolve_local_asr_selection(settings: Mapping[str, object]) -> LocalASRSelection:
    """Resolve legacy/current settings into one coherent Local ASR selection."""
    settings = settings or {}
    engine = normalize_asr_engine(str(settings.get("engine") or ""))
    device = str(settings.get("device") or "").strip().lower()
    compute_type = str(settings.get("compute_type") or "").strip()
    profile_name = str(settings.get("profile_name") or "Custom")

    # Backwards compatibility for the previous sentinel-like storage shape.
    if device in {ASR_DEVICE_VULKAN, "whispercpp", "whisper.cpp"} or compute_type.casefold() in {
        "vulkan",
        "whispercpp",
        "whisper.cpp",
    }:
        engine = ASR_ENGINE_WHISPERCPP_VULKAN

    if engine == ASR_ENGINE_WHISPERCPP_VULKAN:
        return LocalASRSelection(
            engine_id=ASR_ENGINE_WHISPERCPP_VULKAN,
            profile_name=ASR_BEST_TESTED_PROFILE,
            model_name=BENCHMARKED_LOCAL_ASR_MODEL,
            acceleration=ASR_DEVICE_VULKAN,
            faster_whisper_compute_type=None,
            resolved_runner=ASR_RUNNER_WHISPERCPP,
        )

    model_name = str(settings.get("model_name") or "small").strip().lower() or "small"
    acceleration = device if device in {ASR_DEVICE_CPU, ASR_DEVICE_CUDA} else ASR_DEVICE_CPU
    faster_compute = compute_type or "int8"
    return LocalASRSelection(
        engine_id=ASR_ENGINE_FASTER_WHISPER,
        profile_name=profile_name,
        model_name=model_name,
        acceleration=acceleration,
        faster_whisper_compute_type=faster_compute,
        resolved_runner=ASR_RUNNER_FASTER_WHISPER,
    )


def local_asr_settings_from_selection(
    selection: LocalASRSelection,
    *,
    speaker_name: str = "Speaker 1",
    language: str = "",
    initial_prompt: str = "",
) -> dict[str, str]:
    """Return persistable settings from a resolved Local ASR selection."""
    if selection.engine_id == ASR_ENGINE_WHISPERCPP_VULKAN:
        return {
            "engine": ASR_ENGINE_WHISPERCPP_VULKAN,
            "profile_name": ASR_BEST_TESTED_PROFILE,
            "model_name": BENCHMARKED_LOCAL_ASR_MODEL,
            "speaker_name": speaker_name or "Speaker 1",
            "language": language or "",
            "initial_prompt": initial_prompt or "",
            "device": ASR_DEVICE_VULKAN,
            "compute_type": "",
        }

    return {
        "engine": ASR_ENGINE_FASTER_WHISPER,
        "profile_name": selection.profile_name or "Custom",
        "model_name": selection.model_name or "small",
        "speaker_name": speaker_name or "Speaker 1",
        "language": language or "",
        "initial_prompt": initial_prompt or "",
        "device": selection.acceleration or ASR_DEVICE_CPU,
        "compute_type": selection.faster_whisper_compute_type or "int8",
    }


def selection_compute_type_label(selection: LocalASRSelection) -> str:
    """Return the user-facing compute type label for a resolved selection."""
    if selection.engine_id == ASR_ENGINE_WHISPERCPP_VULKAN:
        return "Not applicable"
    return selection.faster_whisper_compute_type or "unknown"


def selection_engine_label(selection: LocalASRSelection) -> str:
    if selection.engine_id == ASR_ENGINE_WHISPERCPP_VULKAN:
        return BENCHMARKED_LOCAL_ASR_ENGINE
    return "faster-whisper"


def acceleration_label(device: str) -> str:
    """Return a user-facing acceleration label for a stored device value."""
    normalized = (device or "").strip().lower()
    if normalized == ASR_DEVICE_VULKAN:
        return BENCHMARKED_LOCAL_ASR_ACCELERATION
    if normalized == ASR_DEVICE_CUDA:
        return "NVIDIA CUDA"
    return "CPU"


def normalize_gpu_vendor_hint(value: str) -> str:
    """Normalize a user/system GPU vendor hint for capability messaging."""
    text = (value or "").casefold()
    if any(token in text for token in ("amd", "radeon", "rx ")):
        return "amd"
    if any(token in text for token in ("nvidia", "geforce", "rtx", "gtx", "cuda")):
        return "nvidia"
    if "intel" in text:
        return "intel"
    return ""


def build_local_asr_capability_lines(
    inputs: LocalASRCapabilityInputs | Mapping[str, object],
) -> tuple[str, ...]:
    """Build deterministic local ASR status lines from caller-supplied facts."""
    if not isinstance(inputs, LocalASRCapabilityInputs):
        inputs = LocalASRCapabilityInputs(
            selection=resolve_local_asr_selection(inputs),
            model_name=str(inputs.get("model_name") or "small"),
            device=str(inputs.get("device") or ASR_DEVICE_CPU),
            compute_type=str(inputs.get("compute_type") or "int8"),
            faster_whisper_available=bool(inputs.get("faster_whisper_available")),
            faster_whisper_error=str(inputs.get("faster_whisper_error") or ""),
            cuda_available=bool(inputs.get("cuda_available")),
            cuda_device_name=str(inputs.get("cuda_device_name") or ""),
            cuda_error=str(inputs.get("cuda_error") or ""),
            whispercpp_vulkan_available=bool(inputs.get("whispercpp_vulkan_available")),
            whispercpp_vulkan_binary_detected=bool(
                inputs.get("whispercpp_vulkan_binary_detected")
            ),
            whispercpp_vulkan_model_detected=bool(
                inputs.get("whispercpp_vulkan_model_detected")
            ),
            gpu_vendor_hint=str(inputs.get("gpu_vendor_hint") or ""),
        )

    selection = inputs.selection or resolve_local_asr_selection(
        {
            "model_name": inputs.model_name,
            "device": inputs.device,
            "compute_type": inputs.compute_type,
        }
    )
    model_name = selection.model_name
    device = selection.acceleration
    vendor = normalize_gpu_vendor_hint(inputs.gpu_vendor_hint or inputs.cuda_device_name)

    lines: list[str] = []

    lines.append("Selected configuration:")
    lines.append(f"- Engine/backend: {selection_engine_label(selection)}")
    lines.append(f"- Acceleration: {acceleration_label(selection.acceleration)}")
    lines.append(f"- Model: {selection.model_name}")
    lines.append(f"- Compute type: {selection_compute_type_label(selection)}")
    lines.append(f"- Resolved runner: {selection.resolved_runner}")

    lines.append("")
    lines.append("Available backends:")
    if inputs.faster_whisper_available:
        lines.append("- faster-whisper backend: Installed")
    else:
        error = (inputs.faster_whisper_error or "").strip()
        lines.append(
            "- faster-whisper backend: Import failed"
            + (f": {error}" if error else ".")
        )

    if device == ASR_DEVICE_CUDA:
        if inputs.cuda_available:
            name = (inputs.cuda_device_name or "NVIDIA CUDA device").strip()
            lines.append(f"[OK] NVIDIA CUDA acceleration appears available: {name}")
        else:
            error = (inputs.cuda_error or "").strip()
            lines.append(
                "[WARNING] NVIDIA CUDA acceleration was selected, but no usable "
                "NVIDIA CUDA runtime/device was detected."
                + (f" {error}" if error else "")
            )
    elif device == ASR_DEVICE_CPU:
        lines.append("[OK] CPU acceleration selected.")

    if model_name in {"medium", "large-v3"} and device == ASR_DEVICE_CPU:
        lines.append(f"[WARNING] {model_name} can be slow on CPU.")

    binary_detected = (
        inputs.whispercpp_vulkan_binary_detected
        or inputs.whispercpp_vulkan_available
    )
    model_detected = (
        inputs.whispercpp_vulkan_model_detected
        or inputs.whispercpp_vulkan_available
    )

    if binary_detected:
        lines.append("[OK] whisper.cpp Vulkan binary detected.")
    else:
        lines.append("[INFO] whisper.cpp Vulkan binary not detected.")

    if model_detected:
        lines.append(f"[OK] whisper.cpp {BENCHMARKED_LOCAL_ASR_MODEL} model detected.")
    else:
        lines.append(f"[INFO] whisper.cpp {BENCHMARKED_LOCAL_ASR_MODEL} model not detected.")

    if inputs.whispercpp_vulkan_available:
        lines.append(
            "[OK] Benchmark-backed local profile detected: "
            f"{BENCHMARKED_LOCAL_ASR_ENGINE} / "
            f"{BENCHMARKED_LOCAL_ASR_ACCELERATION} / "
            f"{BENCHMARKED_LOCAL_ASR_MODEL}."
        )
    else:
        lines.append(
            "[INFO] Benchmark-backed local profile is not fully configured: "
            f"{BENCHMARKED_LOCAL_ASR_ENGINE} / "
            f"{BENCHMARKED_LOCAL_ASR_ACCELERATION} / "
            f"{BENCHMARKED_LOCAL_ASR_MODEL}. Selecting a model does not select Vulkan."
        )
        if vendor == "amd":
            lines.append(
                "[INFO] AMD GPU detected. Vulkan acceleration requires a "
                "configured whisper.cpp Vulkan backend."
            )
        elif not vendor:
            lines.append(
                "[INFO] AMD/Vulkan acceleration requires a configured "
                "whisper.cpp Vulkan backend; faster-whisper CUDA is NVIDIA-only."
            )
        elif vendor == "nvidia":
            lines.append(
                "[INFO] NVIDIA GPUs use the faster-whisper CUDA path when CUDA "
                "is configured; this is separate from whisper.cpp Vulkan."
            )
        elif vendor == "intel":
            lines.append(
                "[INFO] Intel GPU acceleration is not exposed as a usable local "
                "ASR option in this dialog."
            )

    return tuple(lines)


def capability_lines_contain(lines: Sequence[str], text: str) -> bool:
    """Test helper-friendly containment without exposing local paths."""
    needle = (text or "").casefold()
    return any(needle in line.casefold() for line in lines)
