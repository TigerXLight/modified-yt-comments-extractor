from __future__ import annotations

import contextlib
import io
import json

import total_export_prepare_cli
from preservation_backend_plan import (
    build_preservation_backend_plan,
    preservation_backend_plan_to_dict,
)
from preservation_evidence_bundle import (
    build_preservation_evidence_bundle,
    build_preservation_evidence_item,
)


def _run_total_export_prepare_cli(*args: str) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = total_export_prepare_cli.main(list(args))
    return int(code or 0), stdout.getvalue()


def run_self_test() -> None:
    item = build_preservation_evidence_item(
        artifact_id="screenshot",
        artifact_format="png",
        capture_method_id="scrollable_container_screenshot",
    )
    bundle = build_preservation_evidence_bundle(
        source_url="https://www.telegraph.co.uk/news/example/",
        status="manual_supplied",
        items=(item,),
    )
    plan = build_preservation_backend_plan(
        source_url="https://www.telegraph.co.uk/news/example/",
        selected_backend_ids=("manual_local_files",),
        selected_format_ids=("html",),
        selected_capture_method_ids=("scrollable_container_screenshot",),
        media_preservation_choice="select",
        evidence_bundle=bundle,
    )
    data = preservation_backend_plan_to_dict(plan)
    assert data["evidence_bundle"]["status"] == "manual_supplied"
    assert data["evidence_bundle"]["items"][0]["artifact_id"] == "screenshot"
    assert data["evidence_bundle"]["items"][0]["artifact_format"] == "png"
    assert data["evidence_bundle"]["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert "no file open" in data["evidence_bundle"]["scope"]

    code, output = _run_total_export_prepare_cli(
        "--explain-preservation-plan",
        "--source-url",
        "https://www.telegraph.co.uk/news/example/",
        "--preservation-backend",
        "manual_local_files",
        "--preservation-format",
        "html",
        "--media-preservation-choice",
        "select",
        "--capture-method",
        "scrollable_container_screenshot",
        "--evidence-bundle-status",
        "manual_supplied",
        "--evidence-item",
        "screenshot:png:scrollable_container_screenshot",
        "--preservation-notes",
        "Local backup plan.",
    )
    assert code == 0
    assert "Status: ready" in output
    assert "manual_local_files" in output
    assert "Media preservation choice: select" in output
    assert "Evidence bundle:" in output
    assert "status: manual_supplied" in output
    assert "item screenshot: format=png" in output
    assert "scrollable_container_screenshot" in output
    assert "focused or selected" in output
    assert "no file open" in output

    code, json_output = _run_total_export_prepare_cli(
        "--explain-preservation-plan",
        "--json",
        "--source-url",
        "https://www.telegraph.co.uk/news/example/",
        "--preservation-backend",
        "manual_local_files",
        "--preservation-format",
        "html",
        "--media-preservation-choice",
        "select",
        "--capture-method",
        "scrollable_container_screenshot",
        "--evidence-bundle-status",
        "manual_supplied",
        "--evidence-item",
        "screenshot:png:scrollable_container_screenshot",
        "--preservation-notes",
        "Local backup plan.",
    )
    assert code == 0
    payload = json.loads(json_output)
    assert payload["evidence_bundle"]["status"] == "manual_supplied"
    assert payload["evidence_bundle"]["items"][0]["artifact_id"] == "screenshot"
    assert payload["evidence_bundle"]["items"][0]["artifact_format"] == "png"
    assert payload["evidence_bundle"]["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert "no file open" in payload["evidence_bundle"]["scope"]

    print("Preservation evidence bundle plan integration self-test passed.")


if __name__ == "__main__":
    run_self_test()
