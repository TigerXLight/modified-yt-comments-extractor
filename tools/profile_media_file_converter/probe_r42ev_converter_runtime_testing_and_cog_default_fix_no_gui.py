from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
text = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
checks = {
    "compression_default_playback_speed_ui_label_1x": '"playback_speed": "1.0x"' in text,
    "compression_normalises_playback_speed_to_ui_label": 'merged["playback_speed"] = speed_label if speed_label in self._file_converter_allowed_playback_speeds() else "1.0x"' in text,
    "file_converter_cog_lift_helper_present": "def _keep_cog_visible()" in text and "settings_button.lift()" in text,
    "file_converter_cog_lift_deferred_present": "self.after(50, _keep_cog_visible)" in text and "self.after(250, _keep_cog_visible)" in text,
    "convert_advanced_tabs_retained": 'values=["Image", "Video", "Audio"]' in text and '"Image defaults / handling"' in text and '"Video defaults / handling"' in text and '"Audio defaults / handling"' in text,
    "compression_advanced_tabs_retained": text.count('values=["Image", "Video", "Audio"]') >= 2 and '"Image compression"' in text and '"Video compression"' in text and '"Audio compression"' in text,
    "compression_simple_resolution_controls_retained": '"Image resolution"' in text and '"Video resolution"' in text,
    "only_optimised_speed_presets_kept": '["Optimised", "Speed"]' in text and "Lower Size" not in text,
}
result = {"schema":"ytce.r42ev.converter_runtime_testing_and_cog_default_fix.v1.probe","mode":"NO_GUI_STATIC_CONTRACT_CHECK","checks":checks,"verdict":all(checks.values())}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["verdict"] else 1)
