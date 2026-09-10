from __future__ import annotations
import importlib.util
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "profile_media_file_converter_r42eh.py"
MAIN = ROOT / "main.py"

def _load_profile():
    name = "profile_media_file_converter_r42eh"
    spec = importlib.util.spec_from_file_location(name, PROFILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load profile module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

checks = {}
errors = {}
try:
    py_compile.compile(str(MAIN), doraise=True)
    checks["main_compiles"] = True
except Exception as exc:
    checks["main_compiles"] = False
    errors["main_compile_error"] = repr(exc)
try:
    py_compile.compile(str(PROFILE), doraise=True)
    checks["profile_compiles"] = True
except Exception as exc:
    checks["profile_compiles"] = False
    errors["profile_compile_error"] = repr(exc)
text = PROFILE.read_text(encoding="utf-8", errors="replace")
checks["target_bitrate_safety_margin_present"] = "* 0.82" in text
checks["maxrate_not_135_percent"] = "1.35" not in text[text.find("def _build_video_encoder_args"):text.find("def _select_optimised_video_strategy")]
checks["target_cap_retry_helper_present"] = "def _retry_target_size_cap_if_needed" in text
checks["target_cap_retry_called"] = "target_cap_mb = _target_size_mb_to_float" in text and "_retry_target_size_cap_if_needed(command" in text
checks["no_enlarge_guard_present"] = "kept_original_streams_because_encoded_output_was_larger" in text
checks["side_effect_guard_present"] = "archive_ph_hit" in text and "native_webview2_started" in text
try:
    mod = _load_profile()
    checks["module_import_ok"] = True
    env = mod.probe_environment()
    checks["env_capability_function_ok"] = env.get("capability_profile_function") == "build_converter_optimisation_capability_profile"
except Exception as exc:
    checks["module_import_ok"] = False
    errors["module_error"] = repr(exc)
result = {"schema":"ytce.r42fe.target_size_cap_retry_probe.v1","checks":checks,"errors":errors,"verdict":all(checks.values())}
print(json.dumps(result, indent=2))
sys.exit(0 if result["verdict"] else 1)
