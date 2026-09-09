from __future__ import annotations

import ast
import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "main.py"
PROFILE = ROOT / "profile_media_file_converter_r42eh.py"
text = MAIN.read_text(encoding="utf-8")

def check_contains(name: str, needle: str) -> bool:
    return needle in text

checks = {
    "main_compiles": False,
    "profile_compiles": False,
    "asr_action_control_present": check_contains("present", "def _create_asr_action_control"),
    "full_width_action_button_retained": check_contains("full_width", "width=spec[\"button_width\"]"),
    "ctk_sibling_cog_removed": "settings_button = ctk.CTkButton" not in text[text.find("def _create_asr_action_control"):text.find("def _create_youtube_settings_entry_section")],
    "tk_label_cog_overlay_present": check_contains("tk_label", "settings_button = tk.Label"),
    "no_place_width_height_in_helper": "action_button.place(x=0, y=0, width=" not in text[text.find("def _create_asr_action_control"):text.find("def _create_youtube_settings_entry_section")]
        and "settings_button.place(\n            x=max" not in text[text.find("def _create_asr_action_control"):text.find("def _create_youtube_settings_entry_section")],
    "cog_uses_hover_icon_for_first_paint": check_contains("normal dark", "normal_cog_image = self.asr_cog_icon_hover_image or self.asr_cog_icon_image"),
    "cog_repeated_lift_present": all(s in text for s in ["tkraise()", "after_idle(_set_button_normal)", "1250"]),
    "r42ez_launch_fix_retained": check_contains("ctk place", "CustomTkinter requires width/height on the constructor"),
}
try:
    py_compile.compile(str(MAIN), doraise=True)
    checks["main_compiles"] = True
except Exception as exc:
    checks["main_compile_error"] = repr(exc)
try:
    py_compile.compile(str(PROFILE), doraise=True)
    checks["profile_compiles"] = True
except Exception as exc:
    checks["profile_compile_error"] = repr(exc)

verdict = all(v is True for v in checks.values() if isinstance(v, bool))
print(json.dumps({"schema":"ytce.r42fa.file_converter_cog_seam_repair_probe.v1","checks":checks,"verdict":verdict}, indent=2))
raise SystemExit(0 if verdict else 1)
