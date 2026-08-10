from source_msn_adapter_live_result_reconciler import (
    FAIL,
    PARTIAL,
    PASS,
    UNKNOWN,
    EvidenceFile,
    _status_from_entries,
)


def _entry(kind: str, path: str, hint: str) -> EvidenceFile:
    return EvidenceFile(kind=kind, path=path, size=1, status_hint=hint)


def test_stale_fail_does_not_override_newer_pass() -> None:
    entries = [
        _entry("operator_final_summary", "old/operator_final.md", FAIL),
        _entry("operator_final_summary", "new/operator_final.json", PASS),
    ]
    assert _status_from_entries(entries) == PASS


def test_presence_unknown_files_are_accepted_for_presence_checks() -> None:
    entries = [
        _entry("article_export", "browser_capture/article.txt", UNKNOWN),
        _entry("article_export", "rendered-page.html", UNKNOWN),
    ]
    assert _status_from_entries(entries) == PASS


def test_partial_beats_stale_fail_when_no_pass_exists() -> None:
    entries = [
        _entry("acceptance_report", "old/acceptance.md", FAIL),
        _entry("acceptance_report", "new/acceptance.json", PARTIAL),
    ]
    assert _status_from_entries(entries) == PARTIAL


def test_require_pass_hint_still_gates_without_pass() -> None:
    entries = [_entry("manual_live_result", "manual.json", UNKNOWN)]
    assert _status_from_entries(entries, require_pass_hint=True) == PARTIAL


if __name__ == "__main__":
    test_stale_fail_does_not_override_newer_pass()
    test_presence_unknown_files_are_accepted_for_presence_checks()
    test_partial_beats_stale_fail_when_no_pass_exists()
    test_require_pass_hint_still_gates_without_pass()
    print("MSN live reconciler status precedence self-test passed.")
