from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from capture_manual_live_smoke_observation_packet_store_cli import (
    run_capture_manual_live_smoke_observation_packet_store_cli,
)
from capture_manual_live_smoke_observation_section_closeout import (
    build_capture_manual_live_smoke_observation_section_closeout_report,
)
from capture_manual_live_smoke_observation_section_closeout_store import (
    CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_SECTION_CLOSEOUT_FILENAME,
    capture_manual_live_smoke_observation_section_closeout_store_result_to_json,
    write_capture_manual_live_smoke_observation_section_closeout_report,
)

_GOOD_HASH = "f" * 64


def _closeout_report():
    with TemporaryDirectory() as directory:
        observations_path = Path(directory) / "observations.json"
        observations_path.write_text(
            json.dumps(
                [
                    {
                        "site_id": "msn-news",
                        "display_name": "MSN News",
                        "requested_action": "manual comments observation",
                        "operator_summary": "Safe operator note only.",
                        "observed_artifacts": [
                            {
                                "file_name": "msn-note.json",
                                "sha256": _GOOD_HASH,
                                "byte_count": 11,
                                "role": "operator_note_metadata",
                            }
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )
        stdout = StringIO()
        with redirect_stdout(stdout):
            run_capture_manual_live_smoke_observation_packet_store_cli(
                ["--observations-json", str(observations_path), "--output-directory", str(Path(directory) / "packet")]
            )
        return build_capture_manual_live_smoke_observation_section_closeout_report(
            json.loads(stdout.getvalue())
        )


def test_observation_section_closeout_store_writes_safe_result() -> None:
    with TemporaryDirectory() as directory:
        result = write_capture_manual_live_smoke_observation_section_closeout_report(
            _closeout_report(), directory
        )
        data = result.to_dict()
        written = Path(directory) / CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_SECTION_CLOSEOUT_FILENAME
        assert written.exists()
        assert data["files"][0]["file_name"] == CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_SECTION_CLOSEOUT_FILENAME
        assert data["files"][0]["byte_count"] == len(written.read_bytes())
        assert data["full_local_path_serialized"] is False
        rendered = capture_manual_live_smoke_observation_section_closeout_store_result_to_json(result)
        assert directory not in rendered
        assert "msn-note.json" not in rendered


def test_observation_section_closeout_store_refuses_overwrite_when_requested() -> None:
    with TemporaryDirectory() as directory:
        write_capture_manual_live_smoke_observation_section_closeout_report(_closeout_report(), directory)
        try:
            write_capture_manual_live_smoke_observation_section_closeout_report(
                _closeout_report(), directory, allow_overwrite=False
            )
        except FileExistsError as exc:
            assert CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_SECTION_CLOSEOUT_FILENAME in str(exc)
        else:
            raise AssertionError("overwrite refusal did not trigger")


if __name__ == "__main__":
    test_observation_section_closeout_store_writes_safe_result()
    test_observation_section_closeout_store_refuses_overwrite_when_requested()
    print("Manual live smoke observation section closeout store self-test passed.")
