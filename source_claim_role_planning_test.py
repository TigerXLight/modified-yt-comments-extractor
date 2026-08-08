from source_claim_role_planning import (
    CurrentnessStatus,
    PrimarySourceStatus,
    SourceRole,
    ClaimSourceRolePlan,
    MediaSourceChainPlan,
    build_self_authored_appearance_claim_plan,
    claim_role_summary,
    detect_closed_loop_reporting,
)


def test_self_authored_post_can_be_primary_for_exact_scope() -> None:
    plan = build_self_authored_appearance_claim_plan(
        claim_text="Self-authored post shows hairstyle at a stated time.",
        post_url="https://example.invalid/post/1",
        authored_or_posted_at="2026-05-01T00:00:00Z",
        captured_at_utc="2026-08-08T18:00:00Z",
        event_time_or_claim_time="2026-06-01T00:00:00Z",
        temporal_gap_note="One month before the assessed event.",
    )
    assert plan.claim_source_role == SourceRole.PRIMARY_ORIGINAL_AUTHORED_SOURCE
    assert plan.primary_source_status == PrimarySourceStatus.PRIMARY_SOURCE_LOCATED
    assert plan.currentness_status == CurrentnessStatus.HISTORICAL
    assert "Does not prove unrelated" in plan.source_role_limitation
    assert plan.validates_exact_claim_scope()


def test_closed_loop_reporting_detection() -> None:
    plans = (
        ClaimSourceRolePlan(
            claim_text="Repeated family/authority statement.",
            claim_type="authority_claim",
            claim_source_role=SourceRole.TERTIARY_PROPAGATED_SOURCE,
            source_role_scope="Propagated statement only.",
            source_role_limitation="Original primary source not shown.",
            primary_source_status=PrimarySourceStatus.TERTIARY_PROPAGATED_CLAIM,
        ),
        ClaimSourceRolePlan(
            claim_text="Original media uploader not located.",
            claim_type="source_chain_gap",
            claim_source_role=SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE,
            source_role_scope="Publisher framing only.",
            source_role_limitation="Cannot replace primary source.",
            primary_source_status=PrimarySourceStatus.PRIMARY_SOURCE_NOT_LOCATED,
        ),
    )
    assert detect_closed_loop_reporting(plans) is True


def test_media_source_chain_does_not_make_publisher_primary() -> None:
    chain = MediaSourceChainPlan(
        media_observed_on_url="https://publisher.invalid/story",
        publisher_page_url="https://publisher.invalid/story",
        publisher_name="Example Publisher",
        publisher_headline_or_caption="Circulated conflict/event video",
        visible_source_credit="Agency/source credit visible, original uploader absent.",
        source_chain_gap="Original source not cited.",
        same_media_seen_on_other_urls=("https://social.invalid/repost",),
    )
    assert chain.publisher_is_not_automatically_primary() is True
    data = chain.to_dict()
    assert data["source_role"] == "SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE"
    assert data["primary_source_status"] == "PRIMARY_SOURCE_NOT_LOCATED"


def test_summary_preserves_scope_and_limitation() -> None:
    plan = build_self_authored_appearance_claim_plan(
        claim_text="Self-authored post shows clothing.",
        post_url="https://example.invalid/post/2",
        authored_or_posted_at=None,
        captured_at_utc="2026-08-08T18:00:00Z",
        event_time_or_claim_time=None,
        temporal_gap_note="Post date absent.",
    )
    text = claim_role_summary(plan)
    assert "PRIMARY_ORIGINAL_AUTHORED_SOURCE" in text
    assert "limitation=" in text


def main() -> None:
    test_self_authored_post_can_be_primary_for_exact_scope()
    test_closed_loop_reporting_detection()
    test_media_source_chain_does_not_make_publisher_primary()
    test_summary_preserves_scope_and_limitation()
    print("source_claim_role_planning_test: OK")


if __name__ == "__main__":
    main()
