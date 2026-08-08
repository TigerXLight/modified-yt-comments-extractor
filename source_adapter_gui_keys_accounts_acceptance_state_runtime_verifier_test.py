from source_adapter_gui_keys_accounts_acceptance_state_runtime import build_record
from source_adapter_gui_keys_accounts_acceptance_state_runtime_verifier import verify_record, verify_records


def test_valid_record_has_no_issues():
    record = build_record("valid", input_refs=["source"], output_refs=["receipt"])
    assert verify_record(record) == []


def test_secret_output_is_rejected():
    record = build_record("bad", input_refs=["source"], output_refs=["secret-token"])
    issues = verify_records([record])
    assert any("secret" in issue for issue in issues)


if __name__ == "__main__":
    test_valid_record_has_no_issues()
    test_secret_output_is_rejected()
    print("Source Adapter GUI KEYS Accounts Acceptance State Runtime verifier self-test passed.")
