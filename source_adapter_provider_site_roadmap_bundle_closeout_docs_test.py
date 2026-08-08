from pathlib import Path

doc = Path("SOURCE_ADAPTER_PROVIDER_SITE_ROADMAP_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
assert "# Source Adapter Provider Site Roadmap Bundle Closeout" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_PROVIDER_SITE_ROADMAP_BUNDLE_CLOSEOUT_BUILT" in doc
assert "SOURCE_ADAPTER_PROVIDER_SITE_ROADMAP_BUNDLE_CLOSEOUT_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Provider Site Roadmap Bundle Closeout docs self-test passed.")
