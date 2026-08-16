"""Structural source-criticism model for Profile/Media HOME.

V76K2 rejects benchmark/verdict-oriented claim verification as product logic.
The app records visible evidence materials and source-chain structure instead:
video, audio, image, and corroborated text chains with sustainable markings and
bias notes.  It also records whether a pictured person is actually affiliated
with the claim being evaluated.

This module is deterministic and review-oriented.  It does not crawl the web,
fetch media, infer identities, auto-classify sensitive attributes, or declare
truth/falsity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

PROFILE_MEDIA_SOURCE_CRITICISM_SCHEMA_VERSION = "profile-media-source-criticism-v76k2"

EVIDENCE_VIDEO = "video"
EVIDENCE_AUDIO = "audio"
EVIDENCE_IMAGE = "image"
EVIDENCE_CORROBORATED_TEXT_CHAIN = "corroborated_text_chain"

PRIMARY = "PRIMARY_SELF_AUTHORED_SCOPE"
SECONDARY = "SECONDARY_WITNESS_ACCOUNT"
TERTIARY = "TERTIARY_PROPAGATED_SOURCE"
INTERNAL = "INTERNAL_MEDIA"
REVIEW = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class EvidenceMarking:
    material_type: str
    description: str = ""
    source_address: str = ""
    sustainable_marking: str = ""
    bias_notes: str = ""
    directly_affiliated_with_claim: bool | None = None
    affiliation_note: str = ""
    schema_version: str = PROFILE_MEDIA_SOURCE_CRITICISM_SCHEMA_VERSION
    folder_scan_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceCriticismDecision:
    status: str
    recommended_review_lane: str
    evidence_materials: tuple[EvidenceMarking, ...] = ()
    structural_notes: tuple[str, ...] = ()
    excluded_frameworks: tuple[str, ...] = ("FEVER", "AVeriTeC", "MICE benchmark/verdict logic")
    source_role_candidate: str = REVIEW
    source_role_is_final: bool = False
    schema_version: str = PROFILE_MEDIA_SOURCE_CRITICISM_SCHEMA_VERSION
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_materials"] = [item.to_dict() for item in self.evidence_materials]
        return payload


def build_evidence_marking(
    material_type: object,
    *,
    description: object = "",
    source_address: object = "",
    sustainable_marking: object = "",
    bias_notes: object = "",
    directly_affiliated_with_claim: bool | None = None,
    affiliation_note: object = "",
) -> EvidenceMarking:
    return EvidenceMarking(
        material_type=str(material_type or "").strip().lower(),
        description=str(description or ""),
        source_address=str(source_address or ""),
        sustainable_marking=str(sustainable_marking or ""),
        bias_notes=str(bias_notes or ""),
        directly_affiliated_with_claim=directly_affiliated_with_claim,
        affiliation_note=str(affiliation_note or ""),
    )


def evaluate_structural_source_criticism(markings: Iterable[EvidenceMarking]) -> SourceCriticismDecision:
    items = tuple(markings)
    notes: list[str] = []
    material_types = {item.material_type for item in items}

    if not items:
        return SourceCriticismDecision(
            status="needs_evidence_marking",
            recommended_review_lane="missing_evidence_materials",
            structural_notes=("No video, audio, image, or corroborated text-chain marking was provided.",),
        )

    if any(item.directly_affiliated_with_claim is False for item in items):
        notes.append(
            "Image/person/material is not shown to be affiliated with the claim; do not score the claim as visually supported."
        )
        return SourceCriticismDecision(
            status="review_required_affiliation_gap",
            recommended_review_lane="claim_subject_affiliation_gap",
            evidence_materials=items,
            structural_notes=tuple(notes),
            source_role_candidate=REVIEW,
        )

    if EVIDENCE_VIDEO in material_types or EVIDENCE_AUDIO in material_types:
        notes.append("Video/audio provides direct material evidence, but speaker/scene/source chain still needs marking.")
    if EVIDENCE_IMAGE in material_types:
        notes.append("Image provides visual material evidence only for what is visible and affiliated with the claim.")
    if EVIDENCE_CORROBORATED_TEXT_CHAIN in material_types:
        notes.append("Corroborated text chain may meet secondary-source classification only when chain, markings, and biases are recorded.")

    if EVIDENCE_CORROBORATED_TEXT_CHAIN in material_types and len(items) >= 2:
        role = SECONDARY
        status = "structural_markings_ready_for_review"
    elif material_types & {EVIDENCE_VIDEO, EVIDENCE_AUDIO, EVIDENCE_IMAGE}:
        role = REVIEW
        status = "material_evidence_ready_for_role_review"
    else:
        role = REVIEW
        status = "review_required_unknown_material_chain"

    return SourceCriticismDecision(
        status=status,
        recommended_review_lane="source_role_review",
        evidence_materials=items,
        structural_notes=tuple(notes),
        source_role_candidate=role,
        source_role_is_final=False,
    )


def render_source_criticism_decision(decision: SourceCriticismDecision) -> str:
    lines = [
        "Profile/Media Structural Source Criticism",
        f"Status: {decision.status}",
        f"Review lane: {decision.recommended_review_lane}",
        f"Source role candidate: {decision.source_role_candidate}",
        f"Final role: {decision.source_role_is_final}",
        "",
        "Evidence materials:",
    ]
    for item in decision.evidence_materials:
        aff = "unknown" if item.directly_affiliated_with_claim is None else str(item.directly_affiliated_with_claim)
        lines.append(f"- {item.material_type}: affiliated_with_claim={aff}; marking={item.sustainable_marking or '(none)'}")
    lines.append("")
    lines.append("Structural notes:")
    for note in decision.structural_notes:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("Excluded from product logic: " + ", ".join(decision.excluded_frameworks))
    return "\n".join(lines)
