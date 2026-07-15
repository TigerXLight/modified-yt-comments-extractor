"""Local-only ASR capability wording helpers.

These helpers describe configured local ASR capability. They do not download
models, run transcription, probe providers, or contact a network service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


ASR_DEVICE_CPU = "cpu"
ASR_DEVICE_CUDA = "cuda"
BENCHMARKED_LOCAL_ASR_ENGINE = "whisper.cpp"
BENCHMARKED_LOCAL_ASR_ACCELERATION = "Vulkan"
BENCHMARKED_LOCAL_ASR_MODEL = "large-v3"


@dataclass(frozen=True)
class LocalASRCapabilityInputs:
    """Facts gathered by the caller for local ASR status text."""

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


def acceleration_label(device: str) -> str:
    """Return a user-facing acceleration label for a stored device value."""
    normalized = (device or "").strip().lower()
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

    model_name = (inputs.model_name or "small").strip() or "small"
    device = (inputs.device or ASR_DEVICE_CPU).strip().lower() or ASR_DEVICE_CPU
    compute_type = (inputs.compute_type or "int8").strip() or "int8"
    vendor = normalize_gpu_vendor_hint(inputs.gpu_vendor_hint or inputs.cuda_device_name)

    lines: list[str] = []

    if inputs.faster_whisper_available:
        lines.append("[OK] faster-whisper backend is installed.")
    else:
        error = (inputs.faster_whisper_error or "").strip()
        lines.append(
            "[MISSING] faster-whisper backend import failed"
            + (f": {error}" if error else ".")
        )

    lines.append("[INFO] Engine/backend: faster-whisper")
    lines.append(f"[INFO] Selected acceleration: {acceleration_label(device)}")
    lines.append(f"[INFO] Selected model: {model_name}")
    lines.append(f"[INFO] Selected compute type: {compute_type}")

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
    else:
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
