from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from source_archive_closeout_integration import article_url_without_fragment, normalize_closeout_url, resolve_archive_metadata_inputs


def test_normalize_closeout_url_removes_cmd_caret() -> None:
    url = "https://www.msn.com/a?ocid=edgemobile^&PC=EMMX01#comments"
    assert normalize_closeout_url(url) == "https://www.msn.com/a?ocid=edgemobile&PC=EMMX01#comments"
    assert article_url_without_fragment(url) == "https://www.msn.com/a?ocid=edgemobile&PC=EMMX01"


def test_resolve_archive_metadata_inputs_from_kwargs(tmp_path: Path) -> None:
    out = tmp_path / "closeout"
    out.mkdir()
    (out / "live_capture").mkdir()
    got = resolve_archive_metadata_inputs(kwargs={"output_dir": str(out), "target_url": "https://www.msn.com/a?x=1^&y=2#comments"})
    assert got["output_root"] == str(out)
    assert got["capture_root"] == str(out / "live_capture")
    assert got["target_url"] == "https://www.msn.com/a?x=1&y=2"


def test_resolve_archive_metadata_inputs_from_result(tmp_path: Path) -> None:
    out = tmp_path / "closeout"
    out.mkdir()
    result = SimpleNamespace(output_root=str(out), article_url="https://www.msn.com/news/id?PC=EMMX01#comments")
    got = resolve_archive_metadata_inputs(result=result)
    assert got["output_root"] == str(out)
    assert got["production_root"] == str(out)
    assert got["target_url"] == "https://www.msn.com/news/id?PC=EMMX01"


def run_self_test() -> None:
    import tempfile
    from pathlib import Path

    test_normalize_closeout_url_removes_cmd_caret()
    with tempfile.TemporaryDirectory() as d:
        test_resolve_archive_metadata_inputs_from_kwargs(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_resolve_archive_metadata_inputs_from_result(Path(d))
    print("source_archive_closeout_integration_test OK")


if __name__ == "__main__":
    run_self_test()
