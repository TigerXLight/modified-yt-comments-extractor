"""CustomTkinter dialog for Local ASR settings."""

from __future__ import annotations

import os
import shutil
import threading
from typing import Dict, Optional, Sequence, Tuple

import customtkinter as ctk
from tkinter import messagebox

from asr_quality_policy import build_auto_quality_recommendation
from local_asr_capabilities import (
    ASR_BEST_TESTED_PROFILE,
    ASR_DEVICE_VULKAN,
    ASR_ENGINE_FASTER_WHISPER,
    ASR_ENGINE_WHISPERCPP_VULKAN,
    LocalASRCapabilityInputs,
    build_local_asr_capability_lines,
    local_asr_settings_from_selection,
    resolve_local_asr_selection,
)


ASR_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
ASR_DEVICES = ["cpu", "cuda"]
ASR_WHISPERCPP_MODELS = ["large-v3"]
ASR_COMPUTE_TYPES = [
    "int8",
    "int8_float32",
    "float32",
    "float16",
    "int8_float16",
]
ASR_ENGINE_LABELS = {
    ASR_ENGINE_WHISPERCPP_VULKAN: "whisper.cpp — Vulkan",
    ASR_ENGINE_FASTER_WHISPER: "faster-whisper — CPU / NVIDIA CUDA",
}
ASR_ENGINE_VALUES = [
    ASR_ENGINE_LABELS[ASR_ENGINE_WHISPERCPP_VULKAN],
    ASR_ENGINE_LABELS[ASR_ENGINE_FASTER_WHISPER],
]
LOCAL_ASR_START_FOOTER_BUTTON_TEXT = "Start Full"


def asr_footer_button_layout(action_label: str) -> Dict[str, Dict[str, object]]:
    """Return responsive footer grid specs for ASR settings actions."""
    if action_label == "Start ASR":
        return {
            "check": {"row": 0, "column": 0, "sticky": "w", "width": 140},
            "auto_probe": {"row": 0, "column": 1, "sticky": "ew", "width": 126},
            "self_test": {"row": 0, "column": 2, "sticky": "ew", "width": 118},
            "probe": {"row": 0, "column": 3, "sticky": "ew", "width": 104},
            "cancel": {"row": 1, "column": 2, "sticky": "e", "width": 110},
            "save": {"row": 1, "column": 3, "sticky": "ew", "width": 132},
        }
    return {
        "check": {"row": 0, "column": 0, "sticky": "w", "width": 140},
        "cancel": {"row": 0, "column": 1, "sticky": "e", "width": 110},
        "save": {"row": 0, "column": 2, "sticky": "ew", "width": 140},
    }

ASR_PROFILES = {
    ASR_BEST_TESTED_PROFILE: {
        "engine": ASR_ENGINE_WHISPERCPP_VULKAN,
        "model_name": "large-v3",
        "device": ASR_DEVICE_VULKAN,
        "compute_type": "",
        "note": (
            "Best-tested local profile. Applies: whisper.cpp / Vulkan / "
            "large-v3 using the configured production sidecar runner."
        ),
    },
    "Fast": {
        "engine": ASR_ENGINE_FASTER_WHISPER,
        "model_name": "tiny",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: tiny / cpu / int8. Fastest CPU preset, lowest accuracy.",
    },
    "Balanced": {
        "engine": ASR_ENGINE_FASTER_WHISPER,
        "model_name": "small",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: small / CPU / int8. Faster-whisper preview/balance profile, not the benchmark-backed local best.",
    },
    "Accurate": {
        "engine": ASR_ENGINE_FASTER_WHISPER,
        "model_name": "medium",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: medium / cpu / int8. Better accuracy, slower on CPU.",
    },
    "Maximum": {
        "engine": ASR_ENGINE_FASTER_WHISPER,
        "model_name": "large-v3",
        "device": "cpu",
        "compute_type": "int8",
        "note": "Applies: large-v3 / CPU / int8. Highest faster-whisper CPU model, not Vulkan.",
    },
    "NVIDIA CUDA Fast": {
        "engine": ASR_ENGINE_FASTER_WHISPER,
        "model_name": "small",
        "device": "cuda",
        "compute_type": "float16",
        "note": "Applies: small / NVIDIA CUDA / float16. Requires working NVIDIA/CUDA setup.",
    },
}


def normalize_asr_engine(value: str) -> str:
    """Normalize saved/display ASR engine values."""
    selection = resolve_local_asr_selection({"engine": value})
    if selection.engine_id == ASR_ENGINE_WHISPERCPP_VULKAN:
        return ASR_ENGINE_WHISPERCPP_VULKAN
    return ASR_ENGINE_FASTER_WHISPER


def engine_label_for_id(engine: str) -> str:
    """Return the user-facing label for an ASR engine id."""
    return ASR_ENGINE_LABELS.get(normalize_asr_engine(engine), ASR_ENGINE_LABELS[ASR_ENGINE_FASTER_WHISPER])


def is_whispercpp_engine(engine: str) -> bool:
    return normalize_asr_engine(engine) == ASR_ENGINE_WHISPERCPP_VULKAN


def best_tested_asr_profile_settings() -> Dict[str, str]:
    """Return the benchmark-backed whisper.cpp Vulkan profile settings."""
    return local_asr_settings_from_selection(resolve_local_asr_selection({"engine": ASR_ENGINE_WHISPERCPP_VULKAN}))


def initial_media_selector_label(
    media_options: Sequence[Tuple[str, str]],
    selected_media_path: str = "",
) -> str:
    """Return the initial FILES-backed media selector label."""
    options = tuple(media_options or ())
    selected_media_path = os.path.abspath(selected_media_path) if selected_media_path else ""
    for label, path in options:
        if selected_media_path and os.path.abspath(path) == selected_media_path:
            return label
    if len(options) == 1:
        return options[0][0]
    return ""


def normalize_asr_settings(settings: Dict[str, str]) -> Dict[str, str]:
    """Normalize ASR settings so engine/device/compute agree."""
    selection = resolve_local_asr_selection(settings or {})
    return local_asr_settings_from_selection(
        selection,
        speaker_name=str((settings or {}).get("speaker_name") or "Speaker 1"),
        language=str((settings or {}).get("language") or ""),
        initial_prompt=str((settings or {}).get("initial_prompt") or ""),
    )


class AsrSettingsDialog(ctk.CTkToplevel):
    """Modal dialog for Local ASR settings."""

    def __init__(
        self,
        parent,
        defaults: Dict[str, str],
        title: str = "Local ASR Settings",
        action_label: str = "Save",
        media_options: Sequence[Tuple[str, str]] = (),
        selected_media_path: str = "",
    ) -> None:
        super().__init__(parent)

        self.result: Optional[Dict[str, str]] = None

        self.title(title)
        self.geometry("660x720")
        self.minsize(600, 620)
        self.transient(parent)
        self.grab_set()
        self._asr_check_busy = False
        self._asr_check_generation = 0
        self._asr_check_destroyed = False
        self.media_options = tuple(media_options or ())
        self.media_label_to_path = {
            label: path
            for label, path in self.media_options
        }

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

        defaults = normalize_asr_settings(defaults)
        self.engine_var = ctk.StringVar(
            value=engine_label_for_id(defaults.get("engine", ASR_ENGINE_FASTER_WHISPER))
        )
        self.model_var = ctk.StringVar(value=defaults.get("model_name", "small") or "small")
        self.speaker_var = ctk.StringVar(value=defaults.get("speaker_name", "Speaker 1") or "Speaker 1")
        self.language_var = ctk.StringVar(value=defaults.get("language", "en") or "")
        self.device_var = ctk.StringVar(value=defaults.get("device", "cpu") or "cpu")
        self.compute_type_var = ctk.StringVar(value=defaults.get("compute_type", "int8") or "int8")
        self.profile_var = ctk.StringVar(value=self._infer_profile_name(defaults))
        self.current_profile_name = self.profile_var.get()
        self.custom_profile_settings = {
            "engine": normalize_asr_engine(defaults.get("engine", ASR_ENGINE_FASTER_WHISPER)),
            "model_name": self.model_var.get() or "small",
            "device": self.device_var.get() or "cpu",
            "compute_type": self.compute_type_var.get() or "int8",
        }

        row = 0

        if action_label == "Start ASR":
            media_labels = [label for label, _path in self.media_options]
            selected_label = initial_media_selector_label(
                self.media_options,
                selected_media_path,
            )
            self.media_var = ctk.StringVar(value=selected_label)
            self._label(body, row, "Media file")
            if media_labels:
                self.media_combo = ctk.CTkComboBox(
                    body,
                    values=media_labels,
                    variable=self.media_var,
                )
                self.media_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
            else:
                self.media_combo = ctk.CTkLabel(
                    body,
                    text="Add media with FILES + or drag/drop first",
                    text_color="#ffc107",
                    anchor="w",
                )
                self.media_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
            row += 1

        self._label(body, row, "Engine/backend")
        self.engine_combo = ctk.CTkComboBox(
            body,
            values=ASR_ENGINE_VALUES,
            variable=self.engine_var,
            command=self._apply_engine,
        )
        self.engine_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._hint(
            body,
            row,
            "Offline/local ASR backend. Model choice is separate from acceleration; large-v3 is a model, not Vulkan."
        )
        row += 1

        self._label(body, row, "Profile")
        self.profile_combo = ctk.CTkComboBox(
            body,
            values=[ASR_BEST_TESTED_PROFILE, "Custom", "Fast", "Balanced", "Accurate", "Maximum", "NVIDIA CUDA Fast"],
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

        self.model_label = self._label(body, row, "Model")
        self.model_combo = ctk.CTkComboBox(
            body,
            values=ASR_MODELS,
            variable=self.model_var,
            command=lambda _value: self._mark_custom_profile(),
        )
        self.model_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self.model_hint_label = self._hint(
            body,
            row,
            "These model choices are for faster-whisper CPU/NVIDIA CUDA. The benchmark-backed local Vulkan profile is whisper.cpp / Vulkan / large-v3 when configured."
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

        self.device_label = self._label(body, row, "Acceleration")
        self.device_combo = ctk.CTkComboBox(
            body,
            values=ASR_DEVICES,
            variable=self.device_var,
            command=lambda _value: self._mark_custom_profile(),
        )
        self.device_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self.compute_label = self._label(body, row, "Compute type")
        self.compute_combo = ctk.CTkComboBox(
            body,
            values=ASR_COMPUTE_TYPES,
            variable=self.compute_type_var,
            command=lambda _value: self._mark_custom_profile(),
        )
        self.compute_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self.compute_hint_label = self._hint(
            body,
            row,
            "Recommended CPU default: int8. NVIDIA CUDA users can try float16 or int8_float16; CUDA is not AMD/Vulkan."
        )
        row += 1

        warning = ctk.CTkLabel(
            body,
            text=(
                "CPU warning: medium can be slow and large-v3 can be very slow on CPU. "
                "NVIDIA CUDA is separate from AMD/Vulkan. "
                "Best-tested local Vulkan uses whisper.cpp / Vulkan / large-v3 when the binary and model are configured."
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
            "Click Update ASR Check to check local ASR readiness. The check reports whisper.cpp binary, Vulkan readiness, large-v3 model, faster-whisper, local media tools, and hardware hints without downloading, transcribing, or contacting providers."
        )

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        layout = asr_footer_button_layout(action_label)
        for column in range(4):
            footer.grid_columnconfigure(column, weight=1 if column == 0 else 0)

        self.check_button = ctk.CTkButton(
            footer,
            text="Update ASR Check",
            command=self._check_asr_setup,
            width=int(layout["check"]["width"]),
            fg_color="#3a3a3a",
        )
        self.check_button.grid(
            row=int(layout["check"]["row"]),
            column=int(layout["check"]["column"]),
            sticky=str(layout["check"]["sticky"]),
        )

        if action_label == "Start ASR":
            auto_probe_button = ctk.CTkButton(
                footer,
                text="Auto Probe 30s",
                command=lambda: self._accept_auto_probe(30),
                width=int(layout["auto_probe"]["width"]),
                fg_color="#6a4a1f",
            )
            auto_probe_button.grid(
                row=int(layout["auto_probe"]["row"]),
                column=int(layout["auto_probe"]["column"]),
                sticky=str(layout["auto_probe"]["sticky"]),
                padx=(8, 0),
            )

            calibration_button = ctk.CTkButton(
                footer,
                text="Self-Test 15s",
                command=lambda: self._accept_calibration_probe(15),
                width=int(layout["self_test"]["width"]),
                fg_color="#345a7a",
            )
            calibration_button.grid(
                row=int(layout["self_test"]["row"]),
                column=int(layout["self_test"]["column"]),
                sticky=str(layout["self_test"]["sticky"]),
                padx=(8, 0),
            )

            probe_button = ctk.CTkButton(
                footer,
                text="Probe 60s",
                command=lambda: self._accept_probe(60),
                width=int(layout["probe"]["width"]),
                fg_color="#5a5a5a",
            )
            probe_button.grid(
                row=int(layout["probe"]["row"]),
                column=int(layout["probe"]["column"]),
                sticky=str(layout["probe"]["sticky"]),
                padx=(8, 0),
            )
            save_text = LOCAL_ASR_START_FOOTER_BUTTON_TEXT
        else:
            save_text = action_label

        cancel_button = ctk.CTkButton(
            footer,
            text="Cancel",
            command=self._cancel,
            width=int(layout["cancel"]["width"]),
            fg_color="#3a3a3a",
        )
        cancel_button.grid(
            row=int(layout["cancel"]["row"]),
            column=int(layout["cancel"]["column"]),
            sticky=str(layout["cancel"]["sticky"]),
            padx=(8, 0),
            pady=(8, 0) if action_label == "Start ASR" else 0,
        )

        save_button = ctk.CTkButton(
            footer,
            text=save_text,
            command=self._accept,
            width=int(layout["save"]["width"]),
        )
        save_button.grid(
            row=int(layout["save"]["row"]),
            column=int(layout["save"]["column"]),
            sticky=str(layout["save"]["sticky"]),
            padx=(8, 0),
            pady=(8, 0) if action_label == "Start ASR" else 0,
        )

        self._sync_engine_controls()

        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Control-Return>", lambda _event: self._accept())

        self.after(100, self._focus_first)

    def _label(self, parent, row: int, text: str):
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        label.grid(row=row, column=0, sticky="w", pady=8)
        return label

    def _hint(self, parent, row: int, text: str):
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
        return hint

    def _focus_first(self) -> None:
        try:
            self.engine_combo.focus_set()
        except Exception:
            pass

    def _infer_profile_name(self, defaults: Dict[str, str]) -> str:
        defaults = normalize_asr_settings(defaults)
        engine = normalize_asr_engine(defaults.get("engine", ASR_ENGINE_FASTER_WHISPER))
        if engine == ASR_ENGINE_WHISPERCPP_VULKAN:
            return ASR_BEST_TESTED_PROFILE

        model = (defaults.get("model_name") or "").strip().lower()
        device = (defaults.get("device") or "").strip().lower()
        compute = (defaults.get("compute_type") or "").strip()

        for profile_name, profile in ASR_PROFILES.items():
            if profile.get("engine") != ASR_ENGINE_FASTER_WHISPER:
                continue
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

        return "Custom settings. Manual engine/model/acceleration/compute values are remembered while this dialog is open."

    def _save_custom_profile_settings(self) -> None:
        """Remember manual engine/model/device/compute settings for Custom profile."""
        self.custom_profile_settings = {
            "engine": normalize_asr_engine(self.engine_var.get()),
            "model_name": (self.model_var.get() or "small").strip().lower(),
            "device": (self.device_var.get() or "cpu").strip().lower(),
            "compute_type": (self.compute_type_var.get() or "int8").strip(),
        }

    def _restore_custom_profile_settings(self) -> None:
        """Restore the remembered Custom profile settings."""
        settings = getattr(self, "custom_profile_settings", {}) or {}

        engine = normalize_asr_engine(str(settings.get("engine") or ASR_ENGINE_FASTER_WHISPER))
        self.engine_var.set(engine_label_for_id(engine))
        self.model_var.set(settings.get("model_name") or "small")
        self.device_var.set(settings.get("device") or "cpu")
        self.compute_type_var.set(settings.get("compute_type") or "int8")
        self._sync_engine_controls()

    def _apply_profile(self, profile_name: str) -> None:
        previous_profile = getattr(self, "current_profile_name", "Custom")

        if previous_profile == "Custom" and profile_name != "Custom":
            self._save_custom_profile_settings()

        if profile_name == "Custom":
            self._restore_custom_profile_settings()
            self.current_profile_name = "Custom"
            self.profile_note.configure(text=self._get_profile_note("Custom"))
            self._sync_engine_controls()
            return

        if profile_name not in ASR_PROFILES:
            self.current_profile_name = "Custom"
            self.profile_note.configure(text=self._get_profile_note("Custom"))
            self._sync_engine_controls()
            return

        profile = ASR_PROFILES[profile_name]
        self.engine_var.set(engine_label_for_id(profile["engine"]))
        self.model_var.set(profile["model_name"])
        self.device_var.set(profile["device"])
        self.compute_type_var.set(profile["compute_type"])
        self.current_profile_name = profile_name
        self.profile_note.configure(text=self._get_profile_note(profile_name))
        self._sync_engine_controls()

    def _mark_custom_profile(self) -> None:
        self.profile_var.set("Custom")
        self.current_profile_name = "Custom"
        self._save_custom_profile_settings()
        self.profile_note.configure(text=self._get_profile_note("Custom"))
        self._sync_engine_controls()

    def _apply_engine(self, engine_label: str) -> None:
        engine = normalize_asr_engine(engine_label)
        if engine == ASR_ENGINE_WHISPERCPP_VULKAN:
            self.profile_var.set(ASR_BEST_TESTED_PROFILE)
            self._apply_profile(ASR_BEST_TESTED_PROFILE)
            return

        if self.current_profile_name == ASR_BEST_TESTED_PROFILE:
            self.profile_var.set("Custom")
            self.current_profile_name = "Custom"
            self.model_var.set("small")
            self.device_var.set("cpu")
            self.compute_type_var.set("int8")
            self.profile_note.configure(text=self._get_profile_note("Custom"))
        self._mark_custom_profile()

    def _sync_engine_controls(self) -> None:
        engine = normalize_asr_engine(self.engine_var.get())
        if engine == ASR_ENGINE_WHISPERCPP_VULKAN:
            self.engine_var.set(ASR_ENGINE_LABELS[ASR_ENGINE_WHISPERCPP_VULKAN])
            self.model_combo.configure(values=ASR_WHISPERCPP_MODELS, state="disabled")
            self.device_combo.configure(values=["vulkan"], state="disabled")
            self.compute_combo.configure(values=["Not applicable"], state="disabled")
            self.model_var.set("large-v3")
            self.device_var.set("vulkan")
            self.compute_type_var.set("Not applicable")
            self.model_hint_label.configure(
                text="Best-tested local profile: Engine/backend: whisper.cpp; Acceleration: Vulkan; Model: large-v3."
            )
            self.compute_hint_label.configure(
                text="Compute type does not apply to whisper.cpp. The existing production runner uses the configured Vulkan CLI and large-v3 model."
            )
        else:
            self.engine_var.set(ASR_ENGINE_LABELS[ASR_ENGINE_FASTER_WHISPER])
            self.model_combo.configure(values=ASR_MODELS, state="normal")
            self.device_combo.configure(values=ASR_DEVICES, state="normal")
            self.compute_combo.configure(values=ASR_COMPUTE_TYPES, state="normal")
            if self.model_var.get() not in ASR_MODELS:
                self.model_var.set("small")
            if self.device_var.get() not in ASR_DEVICES:
                self.device_var.set("cpu")
            if self.compute_type_var.get() not in ASR_COMPUTE_TYPES:
                self.compute_type_var.set("int8")
            self.model_hint_label.configure(
                text="These model choices are for faster-whisper CPU/NVIDIA CUDA. The benchmark-backed local Vulkan profile is whisper.cpp / Vulkan / large-v3 when configured."
            )
            self.compute_hint_label.configure(
                text="Recommended CPU default: int8. NVIDIA CUDA users can try float16 or int8_float16; CUDA is not AMD/Vulkan."
            )

    def _collect(self) -> Optional[Dict[str, str]]:
        engine = normalize_asr_engine(self.engine_var.get())
        model_name = (self.model_var.get() or "small").strip().lower()
        speaker_name = (self.speaker_var.get() or "Speaker 1").strip()
        language = (self.language_var.get() or "").strip().lower()
        device = (self.device_var.get() or "cpu").strip().lower()
        compute_type = (self.compute_type_var.get() or "int8").strip()
        initial_prompt = self.prompt_textbox.get("1.0", "end").strip()

        if engine == ASR_ENGINE_WHISPERCPP_VULKAN:
            model_name = "large-v3"
            device = "vulkan"
            compute_type = ""
        else:
            engine = ASR_ENGINE_FASTER_WHISPER

        if model_name not in ASR_MODELS:
            messagebox.showerror(
                "Invalid ASR Model",
                "Choose one of:\n\n" + "\n".join(ASR_MODELS),
                parent=self,
            )
            return None

        if engine == ASR_ENGINE_FASTER_WHISPER and device not in ASR_DEVICES:
            messagebox.showerror(
                "Invalid ASR Device",
                "Choose cpu or cuda.",
                parent=self,
            )
            return None

        if engine == ASR_ENGINE_FASTER_WHISPER and compute_type not in ASR_COMPUTE_TYPES:
            messagebox.showerror(
                "Invalid Compute Type",
                "Choose one of:\n\n" + "\n".join(ASR_COMPUTE_TYPES),
                parent=self,
            )
            return None

        media_file = ""
        if hasattr(self, "media_var"):
            selected_label = (self.media_var.get() or "").strip()
            media_file = self.media_label_to_path.get(selected_label, "")
            if not media_file:
                messagebox.showerror(
                    "Media File Required",
                    "Add a media file to FILES, then choose it here.",
                    parent=self,
                )
                return None

        return {
            "engine": engine,
            "profile_name": self.profile_var.get() or "Custom",
            "model_name": model_name,
            "speaker_name": speaker_name or "Speaker 1",
            "language": language,
            "initial_prompt": initial_prompt,
            "device": device,
            "compute_type": compute_type,
            "media_file": media_file,
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

    def _build_asr_setup_status_text(self, settings: Dict[str, str]) -> str:
        """Build ASR setup status text from local-only probes."""
        lines = []

        try:
            import faster_whisper  # noqa: F401
            faster_whisper_available = True
            faster_whisper_error = ""
        except Exception as error:
            faster_whisper_available = False
            faster_whisper_error = str(error)

        model_name = settings["model_name"]
        device = settings["device"]
        compute_type = settings["compute_type"]
        selection = resolve_local_asr_selection(settings)
        model_name = selection.model_name
        device = selection.acceleration
        compute_type = selection.faster_whisper_compute_type or ""

        cuda_available = False
        cuda_device_name = ""
        cuda_error = ""
        if device == "cuda":
            try:
                import torch

                if torch.cuda.is_available():
                    cuda_available = True
                    cuda_device_name = torch.cuda.get_device_name(0)
            except Exception as error:
                cuda_error = f"Could not check CUDA through torch: {error}"

        whispercpp_vulkan_available = False
        whispercpp_vulkan_binary_detected = False
        whispercpp_vulkan_model_detected = False
        try:
            from asr_whispercpp import (
                is_whispercpp_vulkan_available,
                whispercpp_cli_path,
                whispercpp_model_path,
            )

            whispercpp_vulkan_available = bool(
                is_whispercpp_vulkan_available("large-v3")
            )
            whispercpp_vulkan_binary_detected = whispercpp_cli_path().exists()
            whispercpp_vulkan_model_detected = whispercpp_model_path("large-v3").exists()
        except Exception:
            whispercpp_vulkan_available = False
            whispercpp_vulkan_binary_detected = False
            whispercpp_vulkan_model_detected = False

        lines.append("whisper.cpp readiness:")
        lines.append(
            "whisper.cpp binary: "
            + ("Found" if whispercpp_vulkan_binary_detected else "Not found")
        )
        lines.append(
            "Vulkan support: "
            + ("Ready" if whispercpp_vulkan_available else "Unavailable")
        )
        lines.append(
            "large-v3 model: "
            + ("Found" if whispercpp_vulkan_model_detected else "Not found")
        )
        lines.append(
            "Best-tested profile: "
            + ("Ready" if whispercpp_vulkan_available else "Not ready")
        )
        if not whispercpp_vulkan_binary_detected:
            lines.append(
                "Reason: the configured whisper.cpp Vulkan binary was not found."
            )
        if whispercpp_vulkan_binary_detected and not whispercpp_vulkan_model_detected:
            lines.append("Reason: the configured whisper.cpp large-v3 model was not found.")
        lines.append("")

        lines.extend(
            build_local_asr_capability_lines(
                LocalASRCapabilityInputs(
                    selection=selection,
                    model_name=model_name,
                    device=device,
                    compute_type=compute_type,
                    faster_whisper_available=faster_whisper_available,
                    faster_whisper_error=faster_whisper_error,
                    cuda_available=cuda_available,
                    cuda_device_name=cuda_device_name,
                    cuda_error=cuda_error,
                    whispercpp_vulkan_available=whispercpp_vulkan_available,
                    whispercpp_vulkan_binary_detected=whispercpp_vulkan_binary_detected,
                    whispercpp_vulkan_model_detected=whispercpp_vulkan_model_detected,
                )
            )
        )

        lines.append("")
        lines.extend(build_auto_quality_recommendation(settings))

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

        return "\n".join(lines)

    def _finish_asr_setup_check(self, generation: int, text: str) -> None:
        if getattr(self, "_asr_check_destroyed", False):
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if generation != getattr(self, "_asr_check_generation", 0):
            return
        self._set_setup_status(text)
        self._asr_check_busy = False
        try:
            self.check_button.configure(state="normal")
        except Exception:
            pass

    def _check_asr_setup(self) -> None:
        if getattr(self, "_asr_check_busy", False):
            return

        settings = self._collect()

        if settings is None:
            return

        self._asr_check_busy = True
        self._asr_check_generation = int(getattr(self, "_asr_check_generation", 0)) + 1
        generation = self._asr_check_generation
        self._set_setup_status("Checking local ASR setup...")
        try:
            self.check_button.configure(state="disabled")
        except Exception:
            pass

        def worker() -> None:
            try:
                text = self._build_asr_setup_status_text(settings)
            except Exception:
                text = "ASR setup check failed before completion."

            try:
                self.after(0, lambda: self._finish_asr_setup_check(generation, text))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _accept_calibration_probe(self, seconds: int = 15) -> None:
        result = self._collect()

        if result is None:
            return

        result["probe_seconds"] = 0
        result["auto_probe_seconds"] = 0
        result["calibration_probe_seconds"] = int(seconds)
        self.result = result
        self.destroy()

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

    def destroy(self) -> None:
        self._asr_check_destroyed = True
        try:
            super().destroy()
        except Exception:
            pass


def ask_asr_settings(
    parent,
    defaults: Dict[str, str],
    title: str = "Local ASR Settings",
    action_label: str = "Save",
    media_options: Sequence[Tuple[str, str]] = (),
    selected_media_path: str = "",
) -> Optional[Dict[str, str]]:
    dialog = AsrSettingsDialog(
        parent,
        defaults=defaults,
        title=title,
        action_label=action_label,
        media_options=media_options,
        selected_media_path=selected_media_path,
    )
    parent.wait_window(dialog)
    return dialog.result
