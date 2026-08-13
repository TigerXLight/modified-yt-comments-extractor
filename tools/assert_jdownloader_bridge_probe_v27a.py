from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
build_tool = (ROOT / "third_party" / "jdownloader" / "tools" / "build_internal_jdownloader_runtime.py").read_text(encoding="utf-8")
backend = (ROOT / "jdownloader_internal_backend.py").read_text(encoding="utf-8")
probe_cmd = (ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_PROBE.cmd").read_text(encoding="utf-8")

assert "--release" in build_tool
assert '"8"' in build_tool
assert '"1.6"' not in build_tool
assert "PROBE_BRIDGE_NOT_BUILT" in backend
assert "_default_bridge_runner" in backend
assert "subprocess.run(" in backend
assert "BUILD_INTERNAL_JDOWNLOADER_RUNTIME.cmd" in backend
assert "WindowsApps" not in probe_cmd
assert "Python311" in probe_cmd
print("assert_jdownloader_bridge_probe_v27a OK")
