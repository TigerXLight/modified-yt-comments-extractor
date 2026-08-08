from pathlib import Path
text = Path("SOURCE_ADAPTER_EVIDENCE_EXPORT_RUNTIME_BRIDGE.md").read_text(encoding="utf-8")
for phrase in [
    "SOURCE_ADAPTER_EVIDENCE_EXPORT_RUNTIME_BRIDGE_BUILT",
    "SOURCE_ADAPTER_EVIDENCE_EXPORT_QUEUE_READY",
    "SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_PACKAGE_READY",
    "SOURCE_ADAPTER_RELEASE_INDEX_RUNTIME_PACKAGE_READY",
    "SOURCE_ADAPTER_ARCHIVE_HANDOFF_RUNTIME_PACKAGE_READY",
    "KEYS/ACCOUNTS",
]:
    assert phrase in text, phrase
print("Source Adapter Evidence Export Runtime Bridge docs self-test passed.")
