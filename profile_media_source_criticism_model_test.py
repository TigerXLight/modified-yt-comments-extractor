from __future__ import annotations

from profile_media_source_criticism_model import (
    EVIDENCE_CORROBORATED_TEXT_CHAIN,
    EVIDENCE_IMAGE,
    SECONDARY,
    build_evidence_marking,
    evaluate_structural_source_criticism,
    render_source_criticism_decision,
)


def test_affiliation_gap_is_explicit_review_lane() -> None:
    image = build_evidence_marking(
        EVIDENCE_IMAGE,
        description="Image shows a person, but the person is not affiliated with the claim text.",
        sustainable_marking="screenshot row 1",
        directly_affiliated_with_claim=False,
        affiliation_note="The image subject is not claimed to have made/performed the claim.",
    )
    decision = evaluate_structural_source_criticism([image])
    assert decision.status == "review_required_affiliation_gap"
    assert decision.recommended_review_lane == "claim_subject_affiliation_gap"
    assert decision.source_role_is_final is False
    assert decision.automatic_classification_performed is False
    text = render_source_criticism_decision(decision)
    assert "not shown to be affiliated" in text


def test_collaborated_text_chain_is_structural_not_absolutist_verdict() -> None:
    chain_a = build_evidence_marking(
        EVIDENCE_CORROBORATED_TEXT_CHAIN,
        description="Publisher A repeats a marked court/police chain with bias notes.",
        sustainable_marking="publisher/source/date/byline/outbound basis",
        bias_notes="institutional framing recorded",
        directly_affiliated_with_claim=True,
    )
    chain_b = build_evidence_marking(
        EVIDENCE_CORROBORATED_TEXT_CHAIN,
        description="Publisher B independently marks the same source chain.",
        sustainable_marking="publisher/source/date/byline/outbound basis",
        bias_notes="possible wire repetition checked",
        directly_affiliated_with_claim=True,
    )
    decision = evaluate_structural_source_criticism([chain_a, chain_b])
    assert decision.status == "structural_markings_ready_for_review"
    assert decision.source_role_candidate == SECONDARY
    assert decision.source_role_is_final is False
    assert "AVeriTeC" in decision.excluded_frameworks
    assert decision.media_download_performed is False


if __name__ == "__main__":
    test_affiliation_gap_is_explicit_review_lane()
    test_collaborated_text_chain_is_structural_not_absolutist_verdict()
    print("profile_media_source_criticism_model v76k2 OK")
