from __future__ import annotations

from profile_media_source_role_policy import build_source_role_policy_report, canonical_source_role, normalize_source_role_value
from profile_media_database_index import build_database_index_from_payloads
from profile_media_source_intake import coerce_source_role


def test_source_role_alias_normalizes_legacy_secondary_witness_source() -> None:
    decision = normalize_source_role_value("SECONDARY_WITNESS_SOURCE")
    assert decision.normalized_value == "SECONDARY_WITNESS_ACCOUNT"
    assert decision.alias_used is True
    assert decision.warning == "source_role_alias_normalized:SECONDARY_WITNESS_SOURCE->SECONDARY_WITNESS_ACCOUNT"
    assert canonical_source_role("SECONDARY_WITNESS_SOURCE") == "SECONDARY_WITNESS_ACCOUNT"


def test_source_role_policy_report_keeps_canonical_and_unknown_values() -> None:
    report = build_source_role_policy_report([
        "PRIMARY_SELF_AUTHORED_SCOPE",
        "SECONDARY_WITNESS_SOURCE",
        "TERTIARY_PROPAGATED_SOURCE",
        "not a role",
    ]).to_dict()
    assert report["decision_count"] == 4
    assert report["alias_count"] == 1
    assert report["unknown_count"] == 1
    assert report["folder_scan_performed"] is False
    assert report["automatic_classification_performed"] is False
    assert report["sensitive_identifier_inference_performed"] is False


def test_source_intake_and_index_use_canonical_role() -> None:
    assert str(coerce_source_role("SECONDARY_WITNESS_SOURCE")) == "SECONDARY_WITNESS_ACCOUNT"
    index = build_database_index_from_payloads([
        {
            "database_root": "Demo Database",
            "case_title": "Role Alias Case",
            "sources": [
                {
                    "source_page": "Demo page",
                    "source_title": "Demo source",
                    "source_bucket": "Social Media/Online",
                    "source_role": "SECONDARY_WITNESS_SOURCE",
                    "claim_basis": "WITNESS_ACCOUNT",
                    "currentness_status": "CURRENT",
                }
            ],
            "profiles": [
                {
                    "profile_text": "Name: Demo Person\nDate: 2026-08-16\nText: Demo\nAddress: Cases/Role Alias Case/Sources/Social Media/Online/Demo source\nSource: Demo page",
                    "source_bucket": "Social Media/Online",
                    "source_role": "SECONDARY_WITNESS_SOURCE",
                    "claim_basis": "WITNESS_ACCOUNT",
                    "currentness_status": "CURRENT",
                }
            ],
        }
    ])
    payload = index.to_dict()
    assert payload["sources"][0]["source_role"] == "SECONDARY_WITNESS_ACCOUNT"
    assert payload["profiles"][0]["source_role"] == "SECONDARY_WITNESS_ACCOUNT"
    assert "SECONDARY_WITNESS_ACCOUNT" in payload["source_roles"]
    assert "SECONDARY_WITNESS_SOURCE" not in payload["source_roles"]
    assert any("source_role_alias_normalized" in warning for warning in payload["warnings"])


def main() -> int:
    test_source_role_alias_normalizes_legacy_secondary_witness_source()
    test_source_role_policy_report_keeps_canonical_and_unknown_values()
    test_source_intake_and_index_use_canonical_role()
    print("profile_media_source_role_policy v76e OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
