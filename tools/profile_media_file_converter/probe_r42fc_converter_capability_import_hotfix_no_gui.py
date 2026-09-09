from __future__ import annotations
import importlib.util
import json
import py_compile
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "main.py"
PROFILE = ROOT / "profile_media_file_converter_r42eh.py"
TEXT = PROFILE.read_text(encoding="utf-8")
checks = {
    "main_compiles": False,
    "profile_compiles": False,
    "capability_profile_function_present": "def build_converter_optimisation_capability_profile" in TEXT,
    "system_resource_profile_present": "def _system_resource_profile" in TEXT,
    "runnable_probe_used": "_probe_runnable_video_encoders" in TEXT,
    "benchmark_function_present": "def _benchmark_single_encoder" in TEXT,
    "side_effect_guard_present": "network_actions_performed" in TEXT and "native_webview2_started" in TEXT,
    "probe_environment_exports_capability_function": '"capability_profile_function"' in TEXT,
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
try:
    spec = importlib.util.spec_from_file_location("profile_media_file_converter_r42eh", PROFILE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    env = mod.probe_environment()
    profile = mod.build_converter_optimisation_capability_profile(benchmark=False, timeout=12)
    checks["module_import_ok"] = True
    checks["profile_schema_ok"] = str(profile.get("schema", "")).endswith("optimisation_capability_profile.r42fb")
    checks["profile_has_system"] = isinstance(profile.get("system"), dict)
    checks["profile_has_recommendation"] = isinstance(profile.get("recommendation"), dict)
    checks["env_capability_function_ok"] = env.get("capability_profile_function") == "build_converter_optimisation_capability_profile"
except Exception as exc:
    checks["module_import_ok"] = False
    checks["module_error"] = repr(exc)
verdict = all(v is True for v in checks.values() if isinstance(v, bool))
print(json.dumps({"schema":"ytce.r42fc.converter_capability_probe.v1","checks":checks,"verdict":verdict}, indent=2))
raise SystemExit(0 if verdict else 1)
