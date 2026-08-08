from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from source_adapter_evidence_claim_link_runtime import example_source_adapter_evidence_claim_link_runtime_package, write_source_adapter_evidence_claim_link_runtime_receipts

SCHEMA_VERSION = "source_adapter_evidence_claim_link_runtime_store_v1"
STORE_STATUS = "STORED"


def store_source_adapter_evidence_claim_link_runtime_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package_dict = dict(package or example_source_adapter_evidence_claim_link_runtime_package())
    result = write_source_adapter_evidence_claim_link_runtime_receipts(output_dir=output_dir)
    result["schema_version"] = SCHEMA_VERSION
    result["store_status"] = STORE_STATUS
    return result
