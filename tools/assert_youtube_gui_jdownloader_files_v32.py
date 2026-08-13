from pathlib import Path

queue = Path("youtube_gui_media_queue.py").read_text(encoding="utf-8")
required_queue = [
    "def _load_internal_jdownloader_execution_manifest",
    "def _completed_internal_jdownloader_file_records",
    "def _internal_jdownloader_duplicate_state_warning",
    '"jdownloader_completed_files": list(internal_jdownloader_completed_files)',
    '"jdownloader_duplicate_state_suspected": bool(internal_jdownloader_duplicate_warning)',
    "internal_jdownloader_file_paths = [str(item[\"path\"])",
    "Possible duplicate/list-state",
]
missing = [marker for marker in required_queue if marker not in queue]
if missing:
    raise SystemExit("Missing V32 GUI/JD file-import markers: " + repr(missing))

tests = Path("youtube_gui_media_queue_test.py").read_text(encoding="utf-8")
required_tests = [
    "test_internal_jdownloader_success_manifest_files_are_added_to_files",
    "test_internal_jdownloader_duplicate_timeout_is_reported_in_gui_message",
    "jdownloader_completed_file_count",
    "may already exist in JDownloader LinkGrabber/Downloads",
]
missing_tests = [marker for marker in required_tests if marker not in tests]
if missing_tests:
    raise SystemExit("Missing V32 GUI/JD file-import tests: " + repr(missing_tests))

print("assert_youtube_gui_jdownloader_files_v32 OK")
