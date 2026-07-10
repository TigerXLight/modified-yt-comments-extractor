from __future__ import annotations

import contextlib
import io
import json

import preservation_backend_plan_cli
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


def _run_preservation_backend_plan_cli(*args: str) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = preservation_backend_plan_cli.main(list(args))
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
        "--evidence-item-role",
        "screenshot=primary",
        "--evidence-item-origin",
        "screenshot=manual",
        "--evidence-item-path-hint",
        r"screenshot=captures\comments.png",
        "--evidence-item-notes",
        "screenshot=User supplied screenshot; path hint only.",
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
    assert "role=primary" in output
    assert "origin=manual" in output
    assert r"path_hint=captures\comments.png" in output
    assert "User supplied screenshot; path hint only." in output
    assert "label only; not opened or checked" in output
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
        "--evidence-item-role",
        "screenshot=primary",
        "--evidence-item-origin",
        "screenshot=manual",
        "--evidence-item-path-hint",
        r"screenshot=captures\comments.png",
        "--evidence-item-notes",
        "screenshot=User supplied screenshot; path hint only.",
        "--preservation-notes",
        "Local backup plan.",
    )
    assert code == 0
    payload = json.loads(json_output)
    assert payload["evidence_bundle"]["status"] == "manual_supplied"
    assert payload["evidence_bundle"]["items"][0]["artifact_id"] == "screenshot"
    assert payload["evidence_bundle"]["items"][0]["artifact_format"] == "png"
    assert payload["evidence_bundle"]["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert payload["evidence_bundle"]["items"][0]["artifact_role"] == "primary"
    assert payload["evidence_bundle"]["items"][0]["origin"] == "manual"
    assert payload["evidence_bundle"]["items"][0]["path_hint"] == r"captures\comments.png"
    assert payload["evidence_bundle"]["items"][0]["notes"] == "User supplied screenshot; path hint only."
    assert "no file open" in payload["evidence_bundle"]["scope"]

    # backend CLI accepts item detail flags too
    code, backend_output = _run_preservation_backend_plan_cli(
        "--format",
        "text",
        "--evidence-bundle-status",
        "manual_supplied",
        "--evidence-item",
        "screenshot:png:scrollable_container_screenshot",
        "--evidence-item-role",
        "screenshot=primary",
        "--evidence-item-origin",
        "screenshot=manual",
        "--evidence-item-path-hint",
        r"screenshot=captures\comments.png",
        "--evidence-item-notes",
        "screenshot=User supplied screenshot; path hint only.",
    )
    assert code == 0
    assert "status: manual_supplied" in backend_output
    assert "screenshot: format=png" in backend_output
    assert "role=primary" in backend_output
    assert "origin=manual" in backend_output
    assert r"captures\comments.png" in backend_output
    assert "User supplied screenshot; path hint only." in backend_output

    print("Preservation evidence bundle plan integration self-test passed.")


if __name__ == "__main__":
    run_self_test()
