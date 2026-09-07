from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import wave

from profile_media_file_converter_r42eh import (
    choose_default_target_format,
    detect_file_kind,
    detect_file_profile,
    output_kind_for_format,
    plan_conversion,
    probe_environment,
    run_conversion,
)


def test_kind_and_output_routes() -> None:
    assert detect_file_kind("clip.mp4") == "video"
    assert detect_file_kind("voice.opus") == "audio"
    assert detect_file_kind("photo.webp") == "image"
    assert detect_file_kind("notes.md") == "text"
    assert output_kind_for_format("mp3") == "audio"
    assert output_kind_for_format("webm") == "video"
    assert output_kind_for_format("png") == "image"
    assert output_kind_for_format("html") == "text"
    assert choose_default_target_format("text") == "html"
    assert choose_default_target_format("image") == "webp"
    assert choose_default_target_format("audio") == "mp3"
    assert choose_default_target_format("video") == "mp4"


def test_text_sniff_detects_extensionless_text() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "README_NO_EXTENSION"
        src.write_text("alpha\nbeta\n", encoding="utf-8")
        profile = detect_file_profile(src)
        assert profile["detected_kind"] == "text"
        assert profile["method"] in {"text_sniff", "mimetype", "extension"}


def test_text_conversion_auto_and_keep_original_false_deletes_after_success() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "note.txt"
        src.write_text("alpha\nbeta\n", encoding="utf-8")
        plan = plan_conversion(src, "auto", keep_original=False)
        assert plan["target_format"] == "html"
        assert plan["input_kind"] == "text"
        result = run_conversion(plan)
        assert result["success"] is True
        assert result["original_deleted"] is True
        out = Path(result["output_path"])
        assert out.exists()
        assert "alpha" in out.read_text(encoding="utf-8")
        assert not src.exists()


def test_text_conversion_keep_original_true_keeps_source() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "note.txt"
        src.write_text("one,two\n", encoding="utf-8")
        plan = plan_conversion(src, "csv", keep_original=True)
        result = run_conversion(plan)
        assert result["success"] is True
        assert result["original_deleted"] is False
        assert src.exists()
        assert Path(result["output_path"]).exists()


def test_output_collision_gets_safe_suffix() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "note.txt"
        src.write_text("hello", encoding="utf-8")
        existing = Path(td) / "note.html"
        existing.write_text("already here", encoding="utf-8")
        plan = plan_conversion(src, "html", keep_original=True)
        assert Path(plan["output_path"]).name == "note_converted_2.html"


def test_failed_ffmpeg_conversion_keeps_original() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "bad.mp3"
        src.write_bytes(b"not a valid media stream")
        plan = plan_conversion(src, "wav", keep_original=False)
        result = run_conversion(plan, timeout=20)
        if shutil.which("ffmpeg"):
            assert result["success"] is False
            assert src.exists()
            assert result["original_deleted"] is False
        else:
            assert result["success"] is False
            assert src.exists()
            assert "ffmpeg executable not found" in result.get("error", "")


def test_ffprobe_detects_audio_when_available() -> None:
    if not shutil.which("ffprobe"):
        return
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "tone.unknown"
        with wave.open(str(src), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b"\x00\x00" * 800)
        profile = detect_file_profile(src)
        assert profile["detected_kind"] == "audio"
        assert profile["method"] == "ffprobe"
        assert probe_environment()["side_effects"]["network_actions_performed"] is False


def test_media_plan_is_non_network_and_uses_ffmpeg_shape() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "voice.wav"
        src.write_bytes(b"not-real-wave-but-plan-only")
        plan = plan_conversion(src, "mp3", keep_original=True)
        assert plan["method"] == "ffmpeg"
        assert "-map_metadata" in plan["command"]
        assert plan["destructive_after_success"] is False
        env = probe_environment()
        assert env["side_effects"]["network_actions_performed"] is False
        assert env["side_effects"]["archive_ph_hit"] is False


def main() -> int:
    tests = [
        test_kind_and_output_routes,
        test_text_sniff_detects_extensionless_text,
        test_text_conversion_auto_and_keep_original_false_deletes_after_success,
        test_text_conversion_keep_original_true_keeps_source,
        test_output_collision_gets_safe_suffix,
        test_failed_ffmpeg_conversion_keeps_original,
        test_ffprobe_detects_audio_when_available,
        test_media_plan_is_non_network_and_uses_ffmpeg_shape,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print("[DONE] R42EH file converter auto-detect tests passed without pytest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
