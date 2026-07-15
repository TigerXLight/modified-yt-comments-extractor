"""ASR quality policy and hardware assessment helpers.

This module does not run transcription. It describes what method the app should
prefer when accuracy is the priority and records why a current method may be
only a fallback.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional


BENCHMARKED_LOCAL_ASR_ENGINE = "whisper.cpp"
BENCHMARKED_LOCAL_ASR_ACCELERATION = "Vulkan"
BENCHMARKED_LOCAL_ASR_MODEL = "large-v3"


def _detect_windows_gpu_names() -> List[str]:
    """Return Windows GPU names using WMIC when available."""
    if platform.system().lower() != "windows":
        return []

    try:
        result = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except Exception:
        return []

    names: List[str] = []

    for line in (result.stdout or "").splitlines():
        line = line.strip()

        if not line or line.lower() == "name":
            continue

        names.append(line)

    return names


def detect_asr_environment() -> Dict[str, Any]:
    """Detect relevant ASR environment/hardware facts."""
    gpu_names = _detect_windows_gpu_names()
    gpu_text = " ".join(gpu_names).lower()

    cuda_available = False
    cuda_device_name = ""

    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())

        if cuda_available:
            cuda_device_name = torch.cuda.get_device_name(0)
    except Exception:
        cuda_available = False
        cuda_device_name = ""

    directml_available = False
    onnx_providers: List[str] = []

    try:
        import onnxruntime as ort

        onnx_providers = list(ort.get_available_providers())
        directml_available = "DmlExecutionProvider" in onnx_providers
    except Exception:
        directml_available = False
        onnx_providers = []

    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count() or 0,
        "ffmpeg_path": shutil.which("ffmpeg") or "",
        "vlc_path": shutil.which("vlc") or "",
        "gpu_names": gpu_names,
        "has_nvidia_hint": "nvidia" in gpu_text or "geforce" in gpu_text or "rtx" in gpu_text or "gtx" in gpu_text,
        "has_amd_hint": "amd" in gpu_text or "radeon" in gpu_text,
        "has_intel_gpu_hint": "intel" in gpu_text,
        "cuda_available": cuda_available,
        "cuda_device_name": cuda_device_name,
        "directml_available": directml_available,
        "onnx_providers": onnx_providers,
    }


def detect_benchmarked_whispercpp_vulkan_profile() -> Dict[str, bool]:
    """Detect the benchmark-backed local whisper.cpp Vulkan profile."""
    try:
        from asr_whispercpp import (
            is_whispercpp_vulkan_available,
            whispercpp_cli_path,
            whispercpp_model_path,
        )

        binary_detected = whispercpp_cli_path().exists()
        model_detected = whispercpp_model_path(BENCHMARKED_LOCAL_ASR_MODEL).exists()
        configured = bool(
            is_whispercpp_vulkan_available(BENCHMARKED_LOCAL_ASR_MODEL)
        )
    except Exception:
        binary_detected = False
        model_detected = False
        configured = False

    return {
        "binary_detected": binary_detected,
        "model_detected": model_detected,
        "configured": configured,
    }


def build_auto_quality_recommendation(settings: Optional[Dict[str, str]] = None) -> List[str]:
    """Return human-readable ASR quality recommendations."""
    env = detect_asr_environment()
    benchmarked_profile = detect_benchmarked_whispercpp_vulkan_profile()
    settings = settings or {}

    lines: List[str] = []

    lines.append("Auto Quality policy:")
    lines.append("- Clear audio + common words should be expected to be near-perfect.")
    lines.append("- If common words are wrong, phrase hints are not the fix; the method/settings are unsuitable.")
    lines.append("- Rare words / phrase hints are only for names, fictional terms, acronyms, foreign words, and domain terms.")

    lines.append("")
    lines.append("Hardware / method assessment:")
    lines.append(f"- CPU threads detected: {env.get('cpu_count', 0)}")

    gpu_names = env.get("gpu_names") or []

    if gpu_names:
        lines.append("- GPU(s) detected:")

        for gpu_name in gpu_names:
            lines.append(f"  - {gpu_name}")
    else:
        lines.append("- GPU detection: no GPU name detected through WMIC.")

    if benchmarked_profile.get("binary_detected"):
        lines.append("[OK] whisper.cpp Vulkan binary detected.")
    else:
        lines.append("[INFO] whisper.cpp Vulkan binary not detected.")

    if benchmarked_profile.get("model_detected"):
        lines.append("[OK] whisper.cpp large-v3 model detected.")
    else:
        lines.append("[INFO] whisper.cpp large-v3 model not detected.")

    if benchmarked_profile.get("configured"):
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
            f"{BENCHMARKED_LOCAL_ASR_MODEL}."
        )

    if env.get("cuda_available"):
        device_name = env.get("cuda_device_name") or "CUDA device"
        lines.append(f"[OK] NVIDIA/CUDA path available: {device_name}")
        lines.append(
            "     CUDA is a separate faster-whisper path, not the "
            "benchmark-backed AMD/Vulkan profile."
        )
    else:
        lines.append("[INFO] NVIDIA/CUDA path is not available.")

    if env.get("has_amd_hint"):
        lines.append("[INFO] AMD GPU detected.")
        lines.append("       faster-whisper cannot use AMD through the normal CUDA path.")
        lines.append(
            "       Benchmarked local acceleration uses whisper.cpp / Vulkan / "
            "large-v3 when configured."
        )

    if env.get("has_intel_gpu_hint"):
        lines.append("[INFO] Intel GPU detected.")
        lines.append("       Future local acceleration path should test DirectML/ONNX.")

    if env.get("directml_available"):
        lines.append("[OK] ONNX Runtime DirectML provider appears available.")
        lines.append("     Future DirectML ASR engine can use this for AMD/Intel/NVIDIA Windows GPUs.")
    else:
        lines.append("[INFO] ONNX Runtime DirectML provider is not installed/enabled yet.")

    lines.append("")
    lines.append("Current local fallback:")
    lines.append("- faster-whisper CPU remains available, but CPU speed is a fallback concern, not the accuracy target.")
    lines.append("- If CPU large models are too slow, the app should run a short quality probe before full transcription.")

    selected_model = settings.get("model_name", "")
    selected_device = settings.get("device", "")
    selected_compute = settings.get("compute_type", "")

    if selected_model or selected_device or selected_compute:
        lines.append("")
        lines.append("Current selected settings:")
        lines.append(f"- model={selected_model or 'unknown'}")
        lines.append(f"- device={selected_device or 'unknown'}")
        lines.append(f"- compute={selected_compute or 'unknown'}")

        if selected_model in {"tiny", "base", "small"}:
            lines.append("[WARNING] This selected model should be treated as draft/preview if clear speech is inaccurate.")

    return lines
