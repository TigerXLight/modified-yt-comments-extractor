from __future__ import annotations

from profile_media_source_segment_analysis import analyze_source_segment, analyze_source_segments


def test_first_person_self_claim_is_author_scope_only() -> None:
    segment = analyze_source_segment("14 Jun - 'Shut up you traitorous appeaser. - White\nI received threats after publishing my statement.")
    payload = segment.to_dict()
    assert payload["first_person_author_self_claim_review"] is True
    assert payload["author_identity_needed"] is True
    assert payload["author_scope_only"] is True
    assert payload["source_role_candidate"] == "PRIMARY_SELF_AUTHORED_SCOPE_REVIEW"
    assert payload["role_scope"] == "author_or_speaker_own_claimed_experience_only"


def test_first_person_about_others_does_not_become_primary_for_them() -> None:
    segment = analyze_source_segment("I heard police say they arrested the man, but I did not witness the arrest.")
    payload = segment.to_dict()
    assert payload["first_person_author_self_claim_review"] is True
    assert "first_person_claim_about_other_people_not_primary_for_them" in payload["warnings"]
    assert payload["final_source_role_decision"] is False


def test_authority_repetition_is_tertiary_review_required_without_witness_basis() -> None:
    segment = analyze_source_segment("Police and court officials said the family statement was repeated by the agency.")
    payload = segment.to_dict()
    assert payload["source_role_candidate"] == "TERTIARY_PROPAGATED_SOURCE_REVIEW_REQUIRED"
    assert payload["witness_connectivity_status"] == "review_required_witness_connectivity_not_established"
    assert payload["no_witness_connectivity_found"] is True
    assert "source_chain_basis_review" in payload["review_lanes"]


def test_direct_interviewer_basis_is_recorded_but_not_final() -> None:
    segment = analyze_source_segment("The reporter told us she interviewed the witness directly.")
    payload = segment.to_dict()
    assert payload["direct_interviewer_basis"] is True
    assert payload["source_role_candidate"] == "SECONDARY_WITNESS_ACCOUNT_REVIEW"
    assert payload["final_source_role_decision"] is False


def test_quoted_social_post_requires_preserved_connection() -> None:
    preserved = analyze_source_segment("Quoted post by @example: https://x.com/example/status/1 says the clip is theirs.")
    missing = analyze_source_segment("A tweet claimed the clip was theirs but no account URL was preserved.")
    assert preserved.quoted_post_present is True
    assert preserved.quoted_post_preserved is True
    assert preserved.quoted_post_primary_for_poster_only is True
    assert preserved.role_scope == "poster_authored_post_only_not_underlying_event"
    assert missing.quoted_post_present is True
    assert missing.quoted_post_preserved is False
    assert "quoted_post_source_or_account_not_preserved" in missing.warnings


def test_multiple_segments_are_not_flattened() -> None:
    segments = analyze_source_segments("I received threats.\n\nPolice said a separate court claim was repeated.")
    assert len(segments) == 2
    assert segments[0].source_role_candidate == "PRIMARY_SELF_AUTHORED_SCOPE_REVIEW"
    assert segments[1].source_role_candidate == "TERTIARY_PROPAGATED_SOURCE_REVIEW_REQUIRED"


if __name__ == "__main__":
    test_first_person_self_claim_is_author_scope_only()
    test_first_person_about_others_does_not_become_primary_for_them()
    test_authority_repetition_is_tertiary_review_required_without_witness_basis()
    test_direct_interviewer_basis_is_recorded_but_not_final()
    test_quoted_social_post_requires_preserved_connection()
    test_multiple_segments_are_not_flattened()
    print("profile_media_source_segment_analysis v76p OK")
