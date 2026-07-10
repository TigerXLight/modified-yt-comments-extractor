import io
import json
from contextlib import redirect_stderr, redirect_stdout

from preservation_evidence_bundle_cli import main


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def run_self_test() -> None:
    code, output, error = _run_cli([])
    assert code == 0
    assert error == ""
    assert "status: planned" in output
    assert "no file existence or capture execution is implied" in output

    args = [
        "--source-url",
        "https://www.telegraph.co.uk/news/example/",
        "--bundle-label",
        "Manual evidence",
        "--status",
        "manual_supplied",
        "--item",
        "screenshot:png:scrollable_container_screenshot",
        "--item-role",
        "screenshot=primary",
        "--item-origin",
        "screenshot=manual",
        "--item-path-hint",
        r"screenshot=captures\comments.png",
        "--item-notes",
        "screenshot=CLI supplied screenshot; path hint only.",
    ]
    code, text, error = _run_cli([*args, "--format", "text"])
    assert code == 0
    assert error == ""
    assert "status: manual_supplied" in text
    assert "screenshot: format=png" in text
    assert "role=primary" in text
    assert "origin=manual" in text
    assert r"path_hint=captures\comments.png" in text
    assert "notes=CLI supplied screenshot; path hint only." in text
    assert "focused or selected" in text
    assert "execution=metadata only" in text

    code, json_output, error = _run_cli([*args, "--format", "json"])
    assert code == 0
    assert error == ""
    parsed = json.loads(json_output)
    assert parsed["source_url"] == "https://www.telegraph.co.uk/news/example/"
    assert parsed["status"] == "manual_supplied"
    assert parsed["items"][0]["artifact_id"] == "screenshot"
    assert parsed["items"][0]["artifact_format"] == "png"
    assert parsed["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert parsed["items"][0]["artifact_role"] == "primary"
    assert parsed["items"][0]["origin"] == "manual"
    assert parsed["items"][0]["path_hint"] == r"captures\comments.png"
    assert parsed["items"][0]["notes"] == "CLI supplied screenshot; path hint only."
    assert "no file open" in parsed["scope"]

    code, output, error = _run_cli(["--item", "bad:exe"])
    assert code == 1
    assert output == ""
    assert "invalid artifact format" in error

    code, output, error = _run_cli(["--item", "bad:png:unknown"])
    assert code == 1
    assert output == ""
    assert "invalid capture method ID" in error

    code, output, error = _run_cli(
        ["--item", "screenshot:png", "--item-role", "missing=primary"]
    )
    assert code == 1
    assert output == ""
    assert "unknown artifact IDs" in error

    code, output, error = _run_cli(
        ["--item", "same:png", "--item", "same:html"]
    )
    assert code == 1
    assert output == ""
    assert "duplicate artifact IDs: same" in error

    code, output, error = _run_cli(["--item", "missing_format"])
    assert code == 1
    assert output == ""
    assert "artifact_id:artifact_format" in error


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle CLI self-test passed.")
