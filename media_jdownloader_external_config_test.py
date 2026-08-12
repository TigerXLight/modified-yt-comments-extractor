from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from media_jdownloader_external_config import (
    candidate_jdownloader_source_paths,
    load_jdownloader_external_config,
    resolve_jdownloader_source_path,
    jdownloader_resolution_to_height,
    write_jdownloader_external_config_report,
)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_jdownloader_external_config_from_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(root / "cfg/plugins/youtube/Youtube.json", {
            "maxvideoresolution": "P_2160",
            "dashmuxingenabled": True,
            "segmentloadingenabled": True,
            "metadataenabled": True,
            "imagefilenamepattern": "*VIDEO_NAME* (*QUALITY*).*EXT*",
        })
        _write_json(root / "cfg/plugins/youtube/Youtube.qualitysortidentifierorderresolution.json", ["P_2160", "P_1080"])
        _write_json(root / "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.json", {
            "binarypath": "C:/JD/ffmpeg.exe",
            "binarypathprobe": "C:/JD/ffprobe.exe",
        })
        _write_json(root / "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.muxtomp4command.json", [
            "-i", "%video", "-i", "%audio", "-c:v", "copy", "-c:a", "copy", "%out", "-y"
        ])
        _write_json(root / "cfg/org.jdownloader.extensions.extraction.ExtractionExtension.json", {"enabled": True})
        (root / "license.txt").write_text("GPL", encoding="utf-8")
        (root / "jd/plugins/hoster").mkdir(parents=True)
        (root / "jd/plugins/hoster/YoutubeCom.class").write_bytes(b"class")
        (root / "jd/captcha/methods/example").mkdir(parents=True)
        (root / "jd/captcha/methods/example/Solver.class").write_bytes(b"class")
        (root / "libs/example.jar").parent.mkdir(parents=True)
        (root / "libs/example.jar").write_bytes(b"jar")
        report = load_jdownloader_external_config(root)
        assert report.source_kind == "directory"
        assert report.max_video_resolution == "P_2160"
        assert report.dash_muxing_enabled is True
        assert report.segment_loading_enabled is True
        assert report.metadata_enabled is True
        assert report.ffmpeg_binary_path.endswith("ffmpeg.exe")
        assert report.extraction_extension_enabled is True
        assert report.plugin_class_count == 1
        assert report.youtube_plugin_class_count == 1
        assert report.captcha_method_count == 1
        assert report.libs_count == 1
        assert jdownloader_resolution_to_height(report.max_video_resolution) == 2160
        out = root / "report.json"
        write_jdownloader_external_config_report(root, out)
        assert json.loads(out.read_text(encoding="utf-8"))["source_kind"] == "directory"


def test_resolve_jdownloader_source_path_accepts_zip_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "JDownloader 2.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("cfg/plugins/youtube/Youtube.json", json.dumps({"maxvideoresolution": "P_1080"}))
        resolved = resolve_jdownloader_source_path(zip_path)
        assert resolved == zip_path
        report = load_jdownloader_external_config(zip_path)
        assert report.source_kind == "zip"
        assert report.max_video_resolution == "P_1080"




def test_resolve_jdownloader_source_path_rejects_placeholder() -> None:
    try:
        resolve_jdownloader_source_path("PASTE_REAL_JDOWNLOADER_ZIP_PATH_HERE")
    except FileNotFoundError as exc:
        assert "placeholder" in str(exc).lower()
    else:
        raise AssertionError("placeholder path should not silently resolve to an installed JDownloader folder")


def test_candidate_jdownloader_source_paths_includes_appdata_zip_locations() -> None:
    candidates = tuple(str(path).replace("\\", "/") for path in candidate_jdownloader_source_paths(""))
    assert any(path.endswith("JDownloader 2/JDownloader 2.zip") for path in candidates)
    assert any(path.endswith("JDownloader 2.0/JDownloader 2.0.zip") for path in candidates)


def test_jdownloader_resolution_to_height_fallback() -> None:
    assert jdownloader_resolution_to_height("P_4320") == 4320
    assert jdownloader_resolution_to_height("1080") == 1080
    assert jdownloader_resolution_to_height("bad", default=720) == 720


if __name__ == "__main__":
    test_load_jdownloader_external_config_from_directory()
    test_resolve_jdownloader_source_path_accepts_zip_file()
    test_resolve_jdownloader_source_path_rejects_placeholder()
    test_candidate_jdownloader_source_paths_includes_appdata_zip_locations()
    test_jdownloader_resolution_to_height_fallback()
    print("media_jdownloader_external_config_test OK")
