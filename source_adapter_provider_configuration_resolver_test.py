from source_adapter_provider_configuration_resolver import STATUS, HANDOFF_STATUS, example_source_adapter_provider_configuration_resolver_package
from source_adapter_provider_configuration_resolver_verifier import verify_source_adapter_provider_configuration_resolver_package

p = example_source_adapter_provider_configuration_resolver_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["provider_configuration_row_count"] == 5
v = verify_source_adapter_provider_configuration_resolver_package(p)
assert v["verified"], v
print("Source Adapter Provider Configuration Resolver self-test passed.")
