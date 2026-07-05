"""CustomTkinter dialog for Local ASR settings."""

from __future__ import annotations

from typing import Dict, Optional

import customtkinter as ctk
from tkinter import messagebox


ASR_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
ASR_DEVICES = ["cpu", "cuda"]
ASR_COMPUTE_TYPES = [
    "int8",
    "int8_float32",
    "float32",
    "float16",
    "int8_float16",
]


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
        self.geometry("620x620")
        self.minsize(560, 560)
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

        row = 0

        self._label(body, row, "Model")
        self.model_combo = ctk.CTkComboBox(body, values=ASR_MODELS, variable=self.model_var)
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
        row += 1

        self._hint(
            body,
            row,
            "Use ISO codes like en, ar, fr, de, es. Leave blank for auto-detect."
        )
        row += 1

        self._label(body, row, "Device")
        self.device_combo = ctk.CTkComboBox(body, values=ASR_DEVICES, variable=self.device_var)
        self.device_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._label(body, row, "Compute type")
        self.compute_combo = ctk.CTkComboBox(body, values=ASR_COMPUTE_TYPES, variable=self.compute_type_var)
        self.compute_combo.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=8)
        row += 1

        self._hint(
            body,
            row,
            "Recommended CPU default: int8. CUDA users can try float16 or int8_float16."
        )
        row += 1

        prompt_label = ctk.CTkLabel(
            body,
            text="Known words / prompt",
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
            "Example: Freckelston, Kingman, ZoneX, Nyxara, Caltheris, BLACKED, Nicolas Cage"
        )

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        footer.grid_columnconfigure(0, weight=1)

        cancel_button = ctk.CTkButton(
            footer,
            text="Cancel",
            command=self._cancel,
            width=110,
            fg_color="#3a3a3a",
        )
        cancel_button.grid(row=0, column=1, padx=(8, 0))

        save_button = ctk.CTkButton(
            footer,
            text=action_label,
            command=self._accept,
            width=140,
        )
        save_button.grid(row=0, column=2, padx=(8, 0))

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
            self.model_combo.focus_set()
        except Exception:
            pass

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

    def _accept(self) -> None:
        result = self._collect()

        if result is None:
            return

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
