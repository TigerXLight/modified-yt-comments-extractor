"""CustomTkinter dialog for Local ASR settings."""

from __future__ import annotations

import os
import shutil
from typing import Dict, Optional

import customtkinter as ctk
from tkinter import messagebox

from asr_quality_policy import build_auto_quality_recommendation


ASR_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
ASR_DEVICES = ["cpu", "cuda"]
ASR_COMPUTE_TYPES = [
    "int8",
    "int8_float32",
    "float32",
    "float16",
    "int8_float16",
]

ASR_PROFILES = {
    "Fast": {
        "model_name": "tiny",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: tiny / cpu / int8. Fastest CPU preset, lowest accuracy.",
    },
    "Balanced": {
        "model_name": "small",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: small / cpu / int8. Recommended default balance.",
    },
    "Accurate": {
        "model_name": "medium",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: medium / cpu / int8. Better accuracy, slower on CPU.",
    },
    "Maximum": {
        "model_name": "large-v3",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: large-v3 / cpu / int8. Highest local model, very slow on CPU.",
    },
    "GPU Fast": {
        "model_name": "small",
        "device": "cuda",
        "compute_type": "float16",
        "note": "Applies: small / cuda / float16. Requires working NVIDIA/CUDA setup.",
    },
}


class AsrSettingsDialog(ctk.CTkToplevel):
    """Modal dialog for Local ASR settings."""

    def __init__(
        self,
        parent,
        defaults: Dict[str, str],
        title: str = "Local ASR Settings",
        action_label: str = "Save",
    ) -> None:
        super().__init__(parent)

        self.result: Optional[Dict[str, str]] = None

        self.title(title)
        self.geometry("660x720")
        self.minsize(600, 620)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))

        body = ctk.CTkScrollableFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        body.grid_columnconfigure(1, weight=1)

        self.model_var = ctk.StringVar(value=defaults.get("model_name", "small") or "small")
        self.speaker_var = ctk.StringVar(value=defaults.get("speaker_name", "Speaker 1") or "Speaker 1")
        self.language_var = ctk.StringVar(value=defaults.get("language", "en") or "")
        self.device_var = ctk.StringVar(value=defaults.get("device", "cpu") or "cpu")
        self.compute_type_var = ctk.StringVar(value=defaults.get("compute_type", "int8") or "int8")
        self.profile_var = ctk.StringVar(value=self._infer_profile_name(defaults))
        self.current_profile_name = self.profile_var.get()
        self.custom_profile_settings = {
            "model_name": self.model_var.get() or "small",
            "device": self.device_var.get() or "cpu",
            "compute_type": self.compute_type_var.get() or "int8",
        }

        row = 0

        self._label(body, row, "Engine")
        self.engine_label = ctk.CTkLabel(
            body,
            text="Local faster-whisper",
            anchor="w",
            text_color="#d0d0d0",
        )
        self.engine_label.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._hint(
            body,
            row,
            "Offline/local ASR engine. First use of a model may download model files; after that it can run from cache."
        )
        row += 1

        self._label(body, row, "Profile")
        self.profile_combo = ctk.CTkComboBox(
            body,
            values=["Custom", "Fast", "Balanced", "Accurate", "Maximum", "GPU Fast"],
            variable=self.profile_var,
            command=self._apply_profile,
        )
        self.profile_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self.profile_note = ctk.CTkLabel(
            body,
            text=self._get_profile_note(self.profile_var.get()),
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.profile_note.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        row += 1

        self._label(body, row, "Model")
        self.model_combo = ctk.CTkComboBox(
            body,
            values=ASR_MODELS,
            variable=self.model_var,
            command=lambda _value: self._mark_custom_profile(),
        )
        self.model_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._hint(
            body,
            row,
            "tiny/base are fastest. small is a good default. medium/large-v3 are slower and heavier."
        )
        row += 1

        self._label(body, row, "Speaker label")
        self.speaker_entry = ctk.CTkEntry(body, textvariable=self.speaker_var)
        self.speaker_entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._label(body, row, "Language")
        self.language_entry = ctk.CTkEntry(body, textvariable=self.language_var)
        self.language_entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        self.language_entry.bind("<KeyRelease>", lambda _event: self._mark_custom_profile())
        row += 1

        self._hint(
            body,
            row,
            "Use ISO codes like en, ar, fr, de, es. Leave blank for auto-detect."
        )
        row += 1

        self._label(body, row, "Device")
        self.device_combo = ctk.CTkComboBox(
            body,
            values=ASR_DEVICES,
            variable=self.device_var,
            command=lambda _value: self._mark_custom_profile(),
        )
        self.device_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._label(body, row, "Compute type")
        self.compute_combo = ctk.CTkComboBox(
            body,
            values=ASR_COMPUTE_TYPES,
            variable=self.compute_type_var,
            command=lambda _value: self._mark_custom_profile(),
        )
        self.compute_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._hint(
            body,
            row,
            "Recommended CPU default: int8. CUDA users can try float16 or int8_float16, but CUDA requires a working NVIDIA/CUDA setup."
        )
        row += 1

        warning = ctk.CTkLabel(
            body,
            text=(
                "CPU warning: medium can be slow and large-v3 can be very slow on normal laptops/desktops. "
                "GPU warning: GPU Fast/cuda will fail if NVIDIA/CUDA support is not installed correctly."
            ),
            font=ctk.CTkFont(size=11),
            text_color="#ffc107",
            anchor="w",
            justify="left",
            wraplength=560,
        )
        warning.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        row += 1

        prompt_label = ctk.CTkLabel(
            body,
            text="Rare words / names / phrase hints",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        prompt_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 6))
        row += 1

        self.prompt_textbox = ctk.CTkTextbox(body, height=150, wrap="word")
        self.prompt_textbox.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        self.prompt_textbox.insert("1.0", defaults.get("initial_prompt", "") or "")
        row += 1

        self._hint(
            body,
            row,
            "Use this for rare names, usernames, fictional terms, foreign words, acronyms, unusual spellings, or case-specific vocabulary.\n"
            "Do not use it to fix ordinary English words; if normal words are wrong, use a better model/profile, check the language setting, or improve the audio.\n\n"
            "Example: Freckelston, Kingman, ZoneX, Nyxara, Caltheris, BLACKED, Nicolas Cage"
        )
        row += 1

        setup_status_label = ctk.CTkLabel(
            body,
            text="ASR setup status",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        setup_status_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 6))
        row += 1

        self.setup_status_textbox = ctk.CTkTextbox(
            body,
            height=150,
            wrap="word",
            font=ctk.CTkFont(size=11),
        )
        self.setup_status_textbox.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        self._set_setup_status(
            "Click Update ASR Check to check faster-whisper, selected settings, hardware hints, VLC, FFmpeg, and the Auto Quality policy. Phrase hints are optional and should only be used for rare/special terms."
        )

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        footer.grid_columnconfigure(0, weight=1)

        check_button = ctk.CTkButton(
            footer,
            text="Update ASR Check",
            command=self._check_asr_setup,
            width=140,
            fg_color="#3a3a3a",
        )
        check_button.grid(row=0, column=0, sticky="w")

        if action_label == "Start ASR":
            auto_probe_button = ctk.CTkButton(
                footer,
                text="Auto Probe 30s",
                command=lambda: self._accept_auto_probe(30),
                width=140,
                fg_color="#6a4a1f",
            )
            auto_probe_button.grid(row=0, column=1, padx=(8, 0))

            probe_button = ctk.CTkButton(
                footer,
                text="Probe 60s",
                command=lambda: self._accept_probe(60),
                width=120,
                fg_color="#5a5a5a",
            )
            probe_button.grid(row=0, column=2, padx=(8, 0))
            cancel_column = 3
            save_column = 4
            save_text = "Start Full ASR"
        else:
            cancel_column = 1
            save_column = 2
            save_text = action_label

        cancel_button = ctk.CTkButton(
            footer,
            text="Cancel",
            command=self._cancel,
            width=110,
            fg_color="#3a3a3a",
        )
        cancel_button.grid(row=0, column=cancel_column, padx=(8, 0))

        save_button = ctk.CTkButton(
            footer,
            text=save_text,
            command=self._accept,
            width=140,
        )
        save_button.grid(row=0, column=save_column, padx=(8, 0))

        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Control-Return>", lambda _event: self._accept())

        self.after(100, self._focus_first)

    def _label(self, parent, row: int, text: str) -> None:
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        label.grid(row=row, column=0, sticky="w", pady=8)

    def _hint(self, parent, row: int, text: str) -> None:
        hint = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            anchor="w",
            justify="left",
            wraplength=520,
        )
        hint.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))

    def _focus_first(self) -> None:
        try:
            self.profile_combo.focus_set()
        except Exception:
            pass

    def _infer_profile_name(self, defaults: Dict[str, str]) -> str:
        model = (defaults.get("model_name") or "").strip().lower()
        device = (defaults.get("device") or "").strip().lower()
        compute = (defaults.get("compute_type") or "").strip()

        for profile_name, profile in ASR_PROFILES.items():
            if (
                model == profile["model_name"]
                and device == profile["device"]
                and compute == profile["compute_type"]
            ):
                return profile_name

        return "Custom"

    def _get_profile_note(self, profile_name: str) -> str:
        if profile_name in ASR_PROFILES:
            return ASR_PROFILES[profile_name]["note"]

        return "Custom settings. Manual model/device/compute values are remembered while this dialog is open."

    def _save_custom_profile_settings(self) -> None:
        """Remember manual model/device/compute settings for Custom profile."""
        self.custom_profile_settings = {
            "model_name": (self.model_var.get() or "small").strip().lower(),
            "device": (self.device_var.get() or "cpu").strip().lower(),
            "compute_type": (self.compute_type_var.get() or "int8").strip(),
        }

    def _restore_custom_profile_settings(self) -> None:
        """Restore the remembered Custom profile settings."""
        settings = getattr(self, "custom_profile_settings", {}) or {}

        self.model_var.set(settings.get("model_name") or "small")
        self.device_var.set(settings.get("device") or "cpu")
        self.compute_type_var.set(settings.get("compute_type") or "int8")

    def _apply_profile(self, profile_name: str) -> None:
        previous_profile = getattr(self, "current_profile_name", "Custom")

        if previous_profile == "Custom" and profile_name != "Custom":
            self._save_custom_profile_settings()

        if profile_name == "Custom":
            self._restore_custom_profile_settings()
            self.current_profile_name = "Custom"
            self.profile_note.configure(text=self._get_profile_note("Custom"))
            return

        if profile_name not in ASR_PROFILES:
            self.current_profile_name = "Custom"
            self.profile_note.configure(text=self._get_profile_note("Custom"))
            return

        profile = ASR_PROFILES[profile_name]
        self.model_var.set(profile["model_name"])
        self.device_var.set(profile["device"])
        self.compute_type_var.set(profile["compute_type"])
        self.current_profile_name = profile_name
        self.profile_note.configure(text=self._get_profile_note(profile_name))

    def _mark_custom_profile(self) -> None:
        self.profile_var.set("Custom")
        self.current_profile_name = "Custom"
        self._save_custom_profile_settings()
        self.profile_note.configure(text=self._get_profile_note("Custom"))

    def _collect(self) -> Optional[Dict[str, str]]:
        model_name = (self.model_var.get() or "small").strip().lower()
        speaker_name = (self.speaker_var.get() or "Speaker 1").strip()
        language = (self.language_var.get() or "").strip().lower()
        device = (self.device_var.get() or "cpu").strip().lower()
        compute_type = (self.compute_type_var.get() or "int8").strip()
        initial_prompt = self.prompt_textbox.get("1.0", "end").strip()

        if model_name not in ASR_MODELS:
            messagebox.showerror(
                "Invalid ASR Model",
                "Choose one of:\n\n" + "\n".join(ASR_MODELS),
                parent=self,
            )
            return None

        if device not in ASR_DEVICES:
            messagebox.showerror(
                "Invalid ASR Device",
                "Choose cpu or cuda.",
                parent=self,
            )
            return None

        if compute_type not in ASR_COMPUTE_TYPES:
            messagebox.showerror(
                "Invalid Compute Type",
                "Choose one of:\n\n" + "\n".join(ASR_COMPUTE_TYPES),
                parent=self,
            )
            return None

        return {
            "model_name": model_name,
            "speaker_name": speaker_name or "Speaker 1",
            "language": language,
            "initial_prompt": initial_prompt,
            "device": device,
            "compute_type": compute_type,
        }

    def _find_vlc_installation(self) -> str:
        """Return VLC/libVLC location if found, otherwise empty string."""
        candidate_paths = [
            os.path.join(os.environ.get("ProgramFiles", ""), "VideoLAN", "VLC", "libvlc.dll"),
            os.path.join(os.environ.get("ProgramFiles", ""), "VideoLAN", "VLC", "vlc.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "VideoLAN", "VLC", "libvlc.dll"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "VideoLAN", "VLC", "vlc.exe"),
        ]

        for candidate in candidate_paths:
            if candidate and os.path.exists(candidate):
                return os.path.dirname(candidate)

        vlc_on_path = shutil.which("vlc")

        if vlc_on_path:
            return vlc_on_path

        return ""

    def _append_media_tools_check_lines(self, lines: list[str]) -> None:
        """Append VLC/ffmpeg check information to ASR setup result."""
        lines.append("")
        lines.append("Media tools:")

        vlc_location = self._find_vlc_installation()

        if vlc_location:
            lines.append(f"[OK] VLC/libVLC found: {vlc_location}")
            lines.append("     Timeline Play/Pause should be available.")
        else:
            lines.append("[MISSING] VLC/libVLC was not found.")
            lines.append("          Install VLC Media Player for transcript timeline Play/Pause.")

        ffmpeg_path = shutil.which("ffmpeg")

        if ffmpeg_path:
            lines.append(f"[OK] FFmpeg found: {ffmpeg_path}")
            lines.append("     Waveform generation should be available.")
        else:
            lines.append("[MISSING] FFmpeg was not found on PATH.")
            lines.append("          Install FFmpeg for waveform generation.")

    def _set_setup_status(self, text: str) -> None:
        """Write setup-check output into the inline status box."""
        if not hasattr(self, "setup_status_textbox"):
            return

        try:
            self.setup_status_textbox.configure(state="normal")
            self.setup_status_textbox.delete("1.0", "end")
            self.setup_status_textbox.insert("1.0", text)
            self.setup_status_textbox.configure(state="disabled")
            self.setup_status_textbox.see("1.0")
        except Exception:
            pass

    def _check_asr_setup(self) -> None:
        settings = self._collect()

        if settings is None:
            return

        lines = []

        try:
            import faster_whisper  # noqa: F401
            lines.append("[OK] faster-whisper is installed.")
        except Exception as error:
            lines.append(f"[MISSING] faster-whisper import failed: {error}")

        model_name = settings["model_name"]
        device = settings["device"]
        compute_type = settings["compute_type"]

        lines.append(f"[INFO] Selected model: {model_name}")
        lines.append(f"[INFO] Selected device: {device}")
        lines.append(f"[INFO] Selected compute type: {compute_type}")

        lines.append("")
        lines.extend(build_auto_quality_recommendation(settings))

        if device == "cuda":
            try:
                import torch

                if torch.cuda.is_available():
                    device_name = torch.cuda.get_device_name(0)
                    lines.append(f"[OK] CUDA appears available: {device_name}")
                else:
                    lines.append("[WARNING] CUDA was selected, but torch.cuda.is_available() returned False.")
            except Exception as error:
                lines.append(f"[WARNING] Could not check CUDA through torch: {error}")
        else:
            lines.append("[OK] CPU mode selected.")

        if device == "cpu" and model_name == "medium":
            lines.append("[WARNING] medium may be slow on CPU.")

        if device == "cpu" and model_name == "large-v3":
            lines.append("[WARNING] large-v3 can be very slow on CPU.")

        if not settings["language"]:
            lines.append("[INFO] Language is blank, so ASR will auto-detect.")
        else:
            lines.append(f"[INFO] Requested language: {settings['language']}")

        if settings["initial_prompt"]:
            lines.append("[OK] Rare words / phrase hints are set.")
        else:
            lines.append("[INFO] Rare words / phrase hints are blank.")

        self._append_media_tools_check_lines(lines)

        lines.append("")
        lines.append("Note: faster-whisper models may download the first time they are used. After that, cached models can be reused.")

        self._set_setup_status("\n".join(lines))

    def _accept_auto_probe(self, seconds: int = 30) -> None:
        result = self._collect()

        if result is None:
            return

        result["probe_seconds"] = 0
        result["auto_probe_seconds"] = int(seconds)
        self.result = result
        self.destroy()

    def _accept_probe(self, seconds: int = 60) -> None:
        result = self._collect()

        if result is None:
            return

        result["probe_seconds"] = int(seconds)
        self.result = result
        self.destroy()

    def _accept(self) -> None:
        result = self._collect()

        if result is None:
            return

        result["probe_seconds"] = 0
        self.result = result
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_asr_settings(
    parent,
    defaults: Dict[str, str],
    title: str = "Local ASR Settings",
    action_label: str = "Save",
) -> Optional[Dict[str, str]]:
    dialog = AsrSettingsDialog(
        parent,
        defaults=defaults,
        title=title,
        action_label=action_label,
    )
    parent.wait_window(dialog)
    return dialog.result
