from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jdownloader_capabilities import build_jdownloader_capabilities_manifest


def _write_fixture(root: Path) -> None:
    hoster = root / "jd" / "plugins" / "hoster"
    decrypter = root / "jd" / "plugins" / "decrypter"
    hoster.mkdir(parents=True)
    decrypter.mkdir(parents=True)
    (hoster / "YoutubeCom.java").write_text(
        '@HostPlugin(names = { "youtube.com", "youtu.be" }, urls = { "" })\npublic class YoutubeCom {}\n',
        encoding="utf-8",
    )
    (decrypter / "TwitterCom.java").write_text(
        '@DecrypterPlugin(names = { "twitter.com", "x.com" }, urls = { "" })\npublic class TwitterCom {}\n',
        encoding="utf-8",
    )
    (hoster / "VimeoCom.class").write_bytes(b"class-placeholder")


def test_manifest_builder_extracts_domains_and_plugin_types() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v66_jd_caps_") as tmp:
        runtime = Path(tmp)
        _write_fixture(runtime)
        manifest = build_jdownloader_capabilities_manifest(runtime_root=runtime)

    assert manifest["schema_version"] == 1
    assert manifest["dev_only"] is True
    assert manifest["startup_safe"] == "not_loaded_on_app_startup"
    assert manifest["counts"]["plugin_files_scanned"] == 3
    assert manifest["counts"]["hoster_plugins"] == 2
    assert manifest["counts"]["decrypter_plugins"] == 1
    assert "youtube.com" in manifest["capabilities"]
    assert "youtu.be" in manifest["capabilities"]
    assert "twitter.com" in manifest["capabilities"]
    assert "x.com" in manifest["capabilities"]
    assert "vimeo.com" in manifest["capabilities"]
    assert manifest["capabilities"]["youtube.com"]["tested"] is True
    assert manifest["capabilities"]["youtube.com"]["supports_video"] is True
    assert "decrypter" in manifest["capabilities"]["twitter.com"]["plugin_types"]


def test_generator_cli_writes_json() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v66_jd_caps_cli_") as tmp:
        runtime = Path(tmp) / "runtime"
        runtime.mkdir()
        _write_fixture(runtime)
        output = Path(tmp) / "jd_capabilities_manifest.json"
        command = [
            sys.executable,
            str(ROOT / "tools" / "generate_jdownloader_capabilities_manifest_v66.py"),
            "--runtime-root",
            str(runtime),
            "--output",
            str(output),
        ]
        completed = subprocess.run(command, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert output.exists()
        manifest = json.loads(output.read_text(encoding="utf-8"))
        assert manifest["counts"]["domains"] >= 5
        assert manifest["runtime_root"] == str(runtime)
        assert "WROTE" in completed.stdout


def test_project_does_not_auto_load_manifest_on_startup() -> None:
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "generate_jdownloader_capabilities_manifest_v66" not in main_source
    assert "jd_capabilities_manifest.json" not in main_source


def main() -> None:
    test_manifest_builder_extracts_domains_and_plugin_types()
    test_generator_cli_writes_json()
    test_project_does_not_auto_load_manifest_on_startup()
    print("assert_jdownloader_capabilities_manifest_v66 OK")


if __name__ == "__main__":
    main()
