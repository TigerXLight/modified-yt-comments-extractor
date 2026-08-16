from __future__ import annotations

from profile_media_database_safety_invariants import audit_payload_safety, combine_safety_audits, render_safety_audit_text


def test_safety_audit_passes_when_flags_are_false():
    audit = audit_payload_safety("demo", {"folder_scan_performed": False, "nested": {"media_download_performed": False}})
    assert audit.status == "passed"
    assert audit.failed_observations == ()
    assert "Status: passed" in render_safety_audit_text(audit)


def test_safety_audit_fails_for_true_forbidden_flags():
    audit = audit_payload_safety("demo", {"scan_folders": True, "nested": {"sensitive_identifier_inference_performed": True}})
    assert audit.status == "failed"
    assert len(audit.failed_observations) == 2
    combined = combine_safety_audits([audit])
    assert combined.status == "failed"


def main() -> int:
    test_safety_audit_passes_when_flags_are_false()
    test_safety_audit_fails_for_true_forbidden_flags()
    print("profile_media_database_safety_invariants v76b OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
