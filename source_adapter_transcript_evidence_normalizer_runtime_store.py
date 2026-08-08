from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_transcript_evidence_normalizer_runtime import example_source_adapter_transcript_evidence_normalizer_runtime_package, write_source_adapter_transcript_evidence_normalizer_runtime_receipts

SCHEMA_VERSION = "source_adapter_transcript_evidence_normalizer_runtime_store_v1"
STORE_STATUS = "STORED"


def store_source_adapter_transcript_evidence_normalizer_runtime_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_source_adapter_transcript_evidence_normalizer_runtime_package())
    result = write_source_adapter_transcript_evidence_normalizer_runtime_receipts(output_dir=output_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS,
        "id": result["id"],
        "status": result["status"],
        "output_file_count": result["output_file_count"],
        "stored_files": result["stored_files"],
    }


if __name__ == "__main__":
    print(json.dumps(store_source_adapter_transcript_evidence_normalizer_runtime_package(), indent=2, sort_keys=True))
