from pathlib import Path
from tempfile import TemporaryDirectory

from profile_media_reddit_comment_tree_extraction_r44j import (
    PASS_STATUS,
    build_large_reddit_thread_policy_r44j,
    choose_reddit_capture_route_r44j,
    parse_ordered_branch_source_r44j,
    parse_reference_markdown_comment_tree_r44j,
    run_self_test,
)


def test_reference_markdown_indentation_scores() -> None:
    text = """# Reddit thread archive — all visible comments, reply-tree indentation, and displayed vote scores
- **Reddit thread counter in screenshots:** `337 comments`
- **Visible/recoverable comment nodes represented in this transcript:** `333`
## Comments
- **1. u/RootUser** — `score: hidden/not shown`
  root body
  - **2. u/ChildUser** — `score: -4`
    child body
    - **3. u/GrandChild** — `score: 2`
      grand child body
- **4. u/SecondRoot** — `score: 0`
  second root body
"""
    nodes, meta = parse_reference_markdown_comment_tree_r44j(text)
    assert len(nodes) == 4
    assert meta["reported_comment_count"] == 337
    assert nodes[0].depth == 0
    assert nodes[1].depth == 1
    assert nodes[2].depth == 2
    assert nodes[1].parent_id == nodes[0].comment_id
    assert nodes[2].score_kind == "positive"
    assert nodes[1].score_kind == "negative"
    assert nodes[0].score_kind == "hidden"


def test_branch_order_and_fallback_policy() -> None:
    rows = parse_ordered_branch_source_r44j("""1 - https://www.reddit.com/r/x/comments/a/comment/c1/
2 - https://www.reddit.com/r/x/comments/a/comment/c2/
2.1 - https://www.reddit.com/r/x/comments/a/comment/c21/
""")
    assert [r["label"] for r in rows] == ["1", "2", "2.1"]
    route = choose_reddit_capture_route_r44j(signed_in_profile_available=False, old_reddit_login_gate=True, current_reddit_network_block=False)
    assert route["route"] == "no_login_current_reddit_visible_target_only"
    assert route["bulk_branch_loop_allowed"] is False


def test_large_thread_policy() -> None:
    policy = build_large_reddit_thread_policy_r44j(
        reported_comment_count=1200,
        recovered_comment_count=500,
        branch_url_count=42,
        signed_in_profile_available=True,
    )
    assert policy["large_thread"] is True
    assert policy["requires_resumable_queue"] is True
    assert policy["do_not_invent_missing_nodes"] is True
    assert policy["recommended_max_pages_per_run"] == 1


def test_self_report() -> None:
    with TemporaryDirectory() as td:
        report = run_self_test(Path(td))
        assert report.status == PASS_STATUS
        assert all(check["status"] == "pass" for check in report.checks)


def run_self_test_wrapper() -> None:
    test_reference_markdown_indentation_scores()
    test_branch_order_and_fallback_policy()
    test_large_thread_policy()
    test_self_report()


if __name__ == "__main__":
    run_self_test_wrapper()
    print("profile_media_reddit_comment_tree_extraction_r44j_test: PASS")
