from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum


class RoadmapCoverageStatus(str, Enum):
    IMPLEMENTED_METADATA = "implemented_metadata"
    IMPLEMENTED_EXISTING_BEHAVIOR = "implemented_existing_behavior"
    ROADMAP_ONLY = "roadmap_only"
    OPERATOR_APPROVAL_REQUIRED = "operator_approval_required"
    NOT_STARTED = "not_started"


@dataclass(frozen=True)
class RoadmapCoverageItem:
    requirement: str
    status: RoadmapCoverageStatus
    covered_by: tuple[str, ...] = ()
    remaining_gap: str = ""
    next_layer: str = ""
    duplicate_guard: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class SourceEvidenceRoadmapConsolidationStatus:
    status_id: str
    items: tuple[RoadmapCoverageItem, ...]
    evidence_file_movement_done: bool = False
    completed_evidence_claim_allowed: bool = False

    def by_status(self, status: RoadmapCoverageStatus) -> tuple[RoadmapCoverageItem, ...]:
        return tuple(item for item in self.items if item.status == status)

    def to_dict(self) -> dict[str, object]:
        return {
            "status_id": self.status_id,
            "item_count": len(self.items),
            "implemented_metadata_count": len(self.by_status(RoadmapCoverageStatus.IMPLEMENTED_METADATA)),
            "roadmap_only_count": len(self.by_status(RoadmapCoverageStatus.ROADMAP_ONLY)),
            "operator_approval_required_count": len(self.by_status(RoadmapCoverageStatus.OPERATOR_APPROVAL_REQUIRED)),
            "not_started_count": len(self.by_status(RoadmapCoverageStatus.NOT_STARTED)),
            "evidence_file_movement_done": self.evidence_file_movement_done,
            "completed_evidence_claim_allowed": self.completed_evidence_claim_allowed,
            "items": [item.to_dict() for item in self.items],
        }


def build_default_roadmap_consolidation_status() -> SourceEvidenceRoadmapConsolidationStatus:
    return SourceEvidenceRoadmapConsolidationStatus(
        status_id="source_evidence_roadmap_consolidation_9ddc226_v1",
        items=(
            RoadmapCoverageItem(
                "YouTube transcripts/comments/livechat",
                RoadmapCoverageStatus.IMPLEMENTED_EXISTING_BEHAVIOR,
                covered_by=("existing YouTube transcript/comments/livechat behavior",),
                remaining_gap="Do not regress existing behavior while adding generic Source URL UI.",
            ),
            RoadmapCoverageItem(
                "Source websites/method catalogue",
                RoadmapCoverageStatus.IMPLEMENTED_METADATA,
                covered_by=("source_website_method_catalog.py",),
                next_layer="Adapter-by-adapter implementation and live/manual test receipts.",
            ),
            RoadmapCoverageItem(
                "Source role/claim-level/media-chain planning",
                RoadmapCoverageStatus.IMPLEMENTED_METADATA,
                covered_by=("source_claim_role_planning.py",),
                next_layer="Integrate fields into database review and export UI after schema approval.",
            ),
            RoadmapCoverageItem(
                "Source URL media UI roadmap",
                RoadmapCoverageStatus.IMPLEMENTED_METADATA,
                covered_by=("source_url_media_ui_contract.py",),
                next_layer="Actual GUI layout/workflow implementation.",
            ),
            RoadmapCoverageItem(
                "Offline single-page archive bundle",
                RoadmapCoverageStatus.IMPLEMENTED_METADATA,
                covered_by=("source_offline_preservation_bundle.py",),
                next_layer="Create bundle writer and optional local viewer.",
            ),
            RoadmapCoverageItem(
                "Database recognition/reclassification",
                RoadmapCoverageStatus.IMPLEMENTED_METADATA,
                covered_by=("evidence_database_recognition_plan.py",),
                remaining_gap="No destructive movement or automatic classification.",
                next_layer="Approval-gated real filesystem migration implementation.",
            ),
            RoadmapCoverageItem(
                "Behavior/action log and accountable witnesses",
                RoadmapCoverageStatus.IMPLEMENTED_METADATA,
                covered_by=("source_behavior_provenance_log.py",),
                next_layer="Wire through live approved capture/import/export actions.",
            ),
            RoadmapCoverageItem(
                "Evidence file movement/completed evidence",
                RoadmapCoverageStatus.OPERATOR_APPROVAL_REQUIRED,
                remaining_gap="Real artifact creation/move/hash verification has not run and must not be claimed as complete.",
                next_layer="Operator-approved execution receipts and post-move verification.",
            ),
            RoadmapCoverageItem(
                "Live/browser/network/archive/provider execution",
                RoadmapCoverageStatus.OPERATOR_APPROVAL_REQUIRED,
                remaining_gap="Requires named site/action approval and manual/live smoke receipts.",
            ),
        ),
    )


def roadmap_consolidation_markdown_table(status: SourceEvidenceRoadmapConsolidationStatus | None = None) -> str:
    status = status or build_default_roadmap_consolidation_status()
    lines = ["| Requirement | Status | Covered by | Gap | Next layer |", "| --- | --- | --- | --- | --- |"]
    for item in status.items:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.requirement,
                    item.status.value,
                    ", ".join(item.covered_by) or "—",
                    item.remaining_gap or "—",
                    item.next_layer or "—",
                ]
            )
            + " |"
        )
    return "\n".join(lines)
