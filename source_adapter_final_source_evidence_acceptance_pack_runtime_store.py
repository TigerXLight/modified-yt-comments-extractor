from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from source_adapter_final_source_evidence_acceptance_pack_runtime import FinalSourceEvidenceAcceptancePackRecord, record_from_dict


class RuntimeStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, record: FinalSourceEvidenceAcceptancePackRecord) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        return self.path

    def read_all(self) -> list[FinalSourceEvidenceAcceptancePackRecord]:
        if not self.path.exists():
            return []
        records: list[FinalSourceEvidenceAcceptancePackRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(record_from_dict(json.loads(line)))
        return records


def write_records(path: str | Path, records: Iterable[FinalSourceEvidenceAcceptancePackRecord]) -> Path:
    store = RuntimeStore(path)
    for record in records:
        store.append(record)
    return store.path


def read_records(path: str | Path) -> list[FinalSourceEvidenceAcceptancePackRecord]:
    return RuntimeStore(path).read_all()
