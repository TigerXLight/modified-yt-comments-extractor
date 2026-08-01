import subprocess
import tempfile
from pathlib import Path

import asr_whispercpp


def test_cleanup_removes_only_invocation_owned_empty_files() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        source = root / "source.mp4"
        source.write_bytes(b"source")
        wav = root / "ytce_whispercpp_audio.wav"
        wav.write_bytes(b"wav")
        output_base = root / "ytce_whispercpp_out_run"
        txt = output_base.with_suffix(".txt")
        srt = output_base.with_suffix(".srt")
        unrelated = root / "unrelated.txt"
        similar = root / "ytce_whispercpp_out_run_extra.txt"
        txt.write_bytes(b"")
        srt.write_bytes(b"")
        unrelated.write_bytes(b"keep")
        similar.write_bytes(b"keep")

        metadata = asr_whispercpp._cleanup_whispercpp_invocation_temp_paths(
            source_path=source,
            wav_path=wav,
            output_base=output_base,
            preserve_non_empty_outputs=True,
        )

        assert metadata["whispercpp_temp_cleanup_attempted"] is True
        assert metadata["whispercpp_temp_cleanup_cleaned_count"] == 3
        assert metadata["whispercpp_temp_cleanup_preserved_partial_count"] == 0
        assert not wav.exists()
        assert not txt.exists()
        assert not srt.exists()
        assert source.exists()
        assert unrelated.exists()
        assert similar.exists()
        assert metadata["whispercpp_source_media_preserved"] is True
        assert metadata["whispercpp_cleanup_scope"] == (
            asr_whispercpp.WHISPERCPP_TEMP_CLEANUP_SCOPE
        )


def test_cleanup_preserves_non_empty_partial_outputs_for_review() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        source = root / "source.mp4"
        source.write_bytes(b"source")
        wav = root / "ytce_whispercpp_audio.wav"
        wav.write_bytes(b"wav")
        output_base = root / "ytce_whispercpp_out_run"
        txt = output_base.with_suffix(".txt")
        srt = output_base.with_suffix(".srt")
        json_path = output_base.with_suffix(".json")
        txt.write_text("partial text", encoding="utf-8")
        srt.write_bytes(b"")
        json_path.write_text('{"partial": true}', encoding="utf-8")

        metadata = asr_whispercpp._cleanup_whispercpp_invocation_temp_paths(
            source_path=source,
            wav_path=wav,
            output_base=output_base,
            preserve_non_empty_outputs=True,
        )

        assert not wav.exists()
        assert txt.exists()
        assert not srt.exists()
        assert json_path.exists()
        assert source.exists()
        assert metadata["whispercpp_partial_output_available"] is True
        assert metadata["whispercpp_partial_output_status"] == "user_review_required"
        assert metadata["whispercpp_temp_cleanup_preserved_partial_count"] == 2
        assert sorted(metadata["whispercpp_partial_output_names"]) == sorted(
            [txt.name, json_path.name]
        )


def test_cleanup_never_removes_source_wav_when_no_temp_copy_was_created() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        source_wav = root / "source.wav"
        source_wav.write_bytes(b"source wav")
        output_base = root / "ytce_whispercpp_out_run"
        output_base.with_suffix(".txt").write_bytes(b"")

        metadata = asr_whispercpp._cleanup_whispercpp_invocation_temp_paths(
            source_path=source_wav,
            wav_path=source_wav,
            output_base=output_base,
            preserve_non_empty_outputs=True,
        )

        assert source_wav.exists()
        assert metadata["whispercpp_temp_cleanup_cleaned_count"] == 1
        assert metadata["whispercpp_source_media_preserved"] is True


def test_cleanup_errors_are_recorded_without_broad_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        source = root / "source.mp4"
        source.write_bytes(b"source")
        output_base = root / "ytce_whispercpp_out_run"
        txt = output_base.with_suffix(".txt")
        txt.write_bytes(b"")

        def failing_unlink(path: Path) -> None:
            if path == txt:
                raise PermissionError("delete blocked")
            path.unlink(missing_ok=True)

        metadata = asr_whispercpp._cleanup_whispercpp_invocation_temp_paths(
            source_path=source,
            wav_path=None,
            output_base=output_base,
            preserve_non_empty_outputs=True,
            unlink_func=failing_unlink,
        )

        assert txt.exists()
        assert metadata["whispercpp_temp_cleanup_cleaned_count"] == 0
        assert metadata["whispercpp_temp_cleanup_errors"] == [
            f"{txt.name}: PermissionError"
        ]
        assert source.exists()


def test_transcribe_timeout_preserves_partial_outputs_and_reports_cleanup() -> None:
    original_cli_path = asr_whispercpp.whispercpp_cli_path
    original_model_path = asr_whispercpp.whispercpp_model_path
    original_make_wav = asr_whispercpp._make_wav_for_whispercpp
    original_run = asr_whispercpp._run_whispercpp_command_with_progress
    original_duration = asr_whispercpp._wav_duration_seconds
    messages: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        source = root / "source.mp4"
        source.write_bytes(b"source media")
        cli = root / "whisper-cli.exe"
        model = root / "ggml-large-v3.bin"
        wav = root / "ytce_whispercpp_audio.wav"
        cli.write_bytes(b"cli")
        model.write_bytes(b"model")
        wav.write_bytes(b"wav")

        def fake_run(command: list[str], **_kwargs: object):
            output_base = Path(command[command.index("-of") + 1])
            output_base.with_suffix(".txt").write_text("partial", encoding="utf-8")
            output_base.with_suffix(".srt").write_bytes(b"")
            raise subprocess.TimeoutExpired(command, 120, output="", stderr="")

        try:
            asr_whispercpp.whispercpp_cli_path = lambda: cli
            asr_whispercpp.whispercpp_model_path = lambda _model_name=None: model
            asr_whispercpp._make_wav_for_whispercpp = lambda *_args, **_kwargs: wav
            asr_whispercpp._run_whispercpp_command_with_progress = fake_run
            asr_whispercpp._wav_duration_seconds = lambda _path: 10.0

            try:
                asr_whispercpp.transcribe_media_file_with_whispercpp_vulkan(
                    str(source),
                    language="en",
                    status_callback=messages.append,
                )
            except asr_whispercpp.WhisperCppTranscriptionError as exc:
                error = exc
            else:
                raise AssertionError("Timeout must fail")
        finally:
            asr_whispercpp.whispercpp_cli_path = original_cli_path
            asr_whispercpp.whispercpp_model_path = original_model_path
            asr_whispercpp._make_wav_for_whispercpp = original_make_wav
            asr_whispercpp._run_whispercpp_command_with_progress = original_run
            asr_whispercpp._wav_duration_seconds = original_duration

        cleanup = error.cleanup_metadata
        assert "timed out" in str(error)
        assert "Source media was not removed" in str(error)
        assert source.exists()
        assert not wav.exists()
        assert cleanup["whispercpp_partial_output_available"] is True
        assert cleanup["whispercpp_partial_output_status"] == "user_review_required"
        assert cleanup["whispercpp_temp_cleanup_cleaned_count"] == 2
        assert cleanup["whispercpp_temp_cleanup_preserved_partial_count"] == 1
        assert len(cleanup["whispercpp_partial_output_names"]) == 1
        assert cleanup["whispercpp_partial_output_names"][0].endswith(".txt")
        assert any("Local ASR timed out" in message for message in messages)
        assert any("partial outputs for review" in message for message in messages)


def run_self_test() -> None:
    test_cleanup_removes_only_invocation_owned_empty_files()
    test_cleanup_preserves_non_empty_partial_outputs_for_review()
    test_cleanup_never_removes_source_wav_when_no_temp_copy_was_created()
    test_cleanup_errors_are_recorded_without_broad_failure()
    test_transcribe_timeout_preserves_partial_outputs_and_reports_cleanup()


if __name__ == "__main__":
    run_self_test()
    print("asr_whispercpp_cleanup_test.py: OK")
