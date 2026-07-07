"""Optional runtime path helpers for experimental ASR engines."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_FFMPEG7_SHARED_BIN = Path(r"C:\ffmpeg-7-shared\bin")
FFMPEG7_SHARED_BIN_ENV = "ASR_FFMPEG7_SHARED_BIN"

_DLL_DIRECTORY_HANDLES = []


def add_ffmpeg7_shared_dll_directory() -> bool:
    """
    Add the FFmpeg 7 shared DLL folder for TorchCodec when it is available.

    The folder can be overridden with ASR_FFMPEG7_SHARED_BIN. Missing folders,
    unsupported Python builds, or DLL path registration errors are treated as a
    no-op so normal ASR startup is not affected.
    """
    configured_path = os.getenv(FFMPEG7_SHARED_BIN_ENV)
    dll_dir = Path(configured_path) if configured_path else DEFAULT_FFMPEG7_SHARED_BIN

    if not dll_dir.exists() or not dll_dir.is_dir():
        return False

    add_dll_directory = getattr(os, "add_dll_directory", None)

    if add_dll_directory is None:
        return False

    try:
        handle = add_dll_directory(str(dll_dir))
    except (OSError, ValueError):
        return False

    _DLL_DIRECTORY_HANDLES.append(handle)
    return True

