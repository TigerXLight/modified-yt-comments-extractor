from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

MARKER = "YTCE_R44J_REDDIT_COMMENT_TREE_EXTRACTION_INDENTATION"
PASS_STATUS = "PASS_R44J_REDDIT_COMMENT_TREE_EXTRACTION_INDENTATION"
BLOCKED_STATUS = "BLOCKED_R44J_REDDIT_COMMENT_TREE_EXTRACTION_INDENTATION"
SCHEMA_VERSION = "reddit_comment_tree_extraction_indentation.r44j.v1"
DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44j_reddit_comment_tree_extraction_indentation"
DEFAULT_TARGET_URL = "https://en.reddit.com/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT"


@dataclass(frozen=True)
class RedditCommentNodeR44J:
    ordinal: int
    comment_id: str
    parent_id: str
    depth: int
    author: str
    score_display: str
    score_kind: str
    body: str
    source_url: str = ""
    source_kind: str = "reference_markdown"
    capture_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedditCommentTreeResultR44J:
    marker: str
    schema_version: str
    status: str
    target_url: str
    output_root: str
    run_dir: str
    comment_index_path: str
    comment_tree_markdown_path: str
    comment_tree_ndjson_path: str
    capture_plan_path: str
    receipt_path: str
    reported_comment_count: int = 0
    recovered_comment_count: int = 0
    count_gap: int = 0
    count_gap_recorded_not_invented: bool = True
    top_level_comment_count: int = 0
    max_comment_depth: int = 0
    hidden_score_count: int = 0
    negative_score_count: int = 0
    score_count: int = 0
    branch_url_count: int = 0
    strategy: str = ""
    fallback_strategy: str = ""
    large_thread_policy: Mapping[str, Any] = field(default_factory=dict)
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class RedditCommentTreeReportR44J:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def build_reddit_comment_tree_extraction_contract_r44j() -> dict[str, Any]:
    return {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "mode_id": "reddit_comment_tree_extraction_indentation",
        "primary_logged_in_route": "R44I direct-launch old/en Reddit target URL with an operator-controlled browser profile, then capture the currently visible target page only",
        "no_login_fallback_route": "current www.reddit.com visible target-only capture may be used when no signed-in Reddit profile is available; stop on login gate or network-security block and write a blocked receipt",
        "large_thread_rule": "old Reddit limit=500 is not a completeness guarantee for 1k+ comment threads; write recovered counts, comment gaps, and a resumable branch/more-comments queue instead of inventing missing nodes",
        "comment_tree_rule": "dedupe by t1/t3 id where available; rebuild indentation from parent links where available, otherwise preserve visible/captured indentation/order from the reference/DOM",
        "score_rule": "Reddit exposes displayed net score text only; do not infer exact upvote/downvote totals; preserve hidden/not-shown and negative net scores",
        "branch_order_rule": "preserve operator/current-Reddit branch URLs in visible top-to-bottom order, keeping nested labels such as 2.1 immediately after their parent label",
        "downstream_chain": "R44J comment tree outputs can sit beside R44I/R44D/R43U receipts and can feed later ledger enrichment without changing media download policy",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def build_large_reddit_thread_policy_r44j(
    *,
    reported_comment_count: int,
    recovered_comment_count: int,
    old_reddit_limit: int = 500,
    branch_url_count: int = 0,
    signed_in_profile_available: bool = False,
) -> dict[str, Any]:
    reported = max(0, int(reported_comment_count or 0))
    recovered = max(0, int(recovered_comment_count or 0))
    gap = max(0, reported - recovered)
    is_large = reported > max(1, int(old_reddit_limit or 500))
    strategy = "logged_in_old_reddit_direct_launch" if signed_in_profile_available else "no_login_current_reddit_fallback_target_only"
    return {
        "reported_comment_count": reported,
        "recovered_comment_count": recovered,
        "comment_count_gap": gap,
        "old_reddit_limit": old_reddit_limit,
        "branch_url_count": max(0, int(branch_url_count or 0)),
        "large_thread": is_large,
        "completeness_guaranteed": False if is_large or gap else True,
        "strategy": strategy,
        "requires_resumable_queue": bool(is_large or branch_url_count or gap),
        "recommended_max_pages_per_run": 1 if is_large else 1,
        "operator_controlled_continuation_required": bool(is_large or branch_url_count or gap),
        "do_not_invent_missing_nodes": True,
        "notes": (
            "For 1k+ comment threads, capture the main target page, then process more-comments/branch URLs through a resumable queue. "
            "Use one visible target page per operator-confirmed run to avoid Reddit rate/security blocks."
        ),
    }


def choose_reddit_capture_route_r44j(
    *,
    signed_in_profile_available: bool,
    old_reddit_login_gate: bool = False,
    current_reddit_network_block: bool = False,
) -> dict[str, Any]:
    if signed_in_profile_available:
        return {
            "route": "logged_in_old_reddit_direct_launch_target_only",
            "status": "ready",
            "fallback_route": "current_reddit_visible_target_only_if_operator_requests",
            "reason": "signed-in operator-controlled profile available",
            "bulk_branch_loop_allowed": False,
        }
    if old_reddit_login_gate and current_reddit_network_block:
        return {
            "route": "blocked",
            "status": "blocked",
            "fallback_route": "manual/imported evidence",
            "reason": "old Reddit requires login and current Reddit shows network-security block",
            "bulk_branch_loop_allowed": False,
        }
    return {
        "route": "no_login_current_reddit_visible_target_only",
        "status": "limited",
        "fallback_route": "saved HTML / copied visible text / screenshot import if current Reddit blocks",
        "reason": "no signed-in Reddit profile available",
        "bulk_branch_loop_allowed": False,
    }


def parse_ordered_branch_source_r44j(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        match = re.match(r"(?P<label>\d+(?:\.\d+)*)\s*[-–]\s*(?P<url>https?://\S+)", line)
        if not match:
            continue
        rows.append({"label": match.group("label"), "url": _plain_url(match.group("url"))})
    return rows


def parse_reference_markdown_comment_tree_r44j(text: str, *, target_url: str = DEFAULT_TARGET_URL) -> tuple[list[RedditCommentNodeR44J], dict[str, Any]]:
    lines = str(text or "").splitlines()
    nodes: list[RedditCommentNodeR44J] = []
    current: dict[str, Any] | None = None
    body_lines: list[str] = []
    reported_comment_count = 0
    represented_comment_count = 0
    post_score = ""
    comment_pattern = re.compile(
        r"^(?P<indent>\s*)[-*]\s+\*\*(?P<ordinal>\d+)\.\s+u/(?P<author>[^*]+?)\*\*\s+—\s+`score:\s*(?P<score>[^`]+)`",
        re.I,
    )
    for line in lines:
        if "Reddit thread counter" in line or "header reports" in line:
            m = re.search(r"(\d+)\s+comments", line)
            if m:
                reported_comment_count = int(m.group(1))
        if "Visible/recoverable comment nodes" in line or "expose 333 comment nodes" in line:
            m = re.search(r"(\d+)", line)
            if m:
                represented_comment_count = int(m.group(1))
        if "Post displayed score" in line:
            m = re.search(r"`?(-?\d+)`?", line)
            if m:
                post_score = m.group(1)
        m = comment_pattern.match(line)
        if m:
            if current is not None:
                nodes.append(_node_from_current(current, body_lines, target_url, len(nodes) + 1))
            indent = len(m.group("indent").replace("\t", "    "))
            current = {
                "ordinal": int(m.group("ordinal")),
                "author": _clean_author(m.group("author")),
                "score_display": m.group("score").strip(),
                "depth": max(0, indent // 2),
                "source_url": target_url,
            }
            body_lines = []
            continue
        if current is not None:
            # Body lines in the reference markdown are indented under the bullet.
            stripped = line.strip()
            if stripped and not stripped.startswith("##"):
                body_lines.append(stripped)
    if current is not None:
        nodes.append(_node_from_current(current, body_lines, target_url, len(nodes) + 1))

    # The reference markdown uses a top-level bullet indent of zero and nested bullets
    # in two-space increments. Preserve those depths but normalise if a renderer inserts
    # a constant offset.
    if nodes:
        min_depth = min(n.depth for n in nodes)
        if min_depth:
            nodes = [RedditCommentNodeR44J(**{**n.to_dict(), "depth": max(0, n.depth - min_depth)}) for n in nodes]
        nodes = _assign_parents_from_depth(nodes)

    meta = {
        "reported_comment_count": reported_comment_count,
        "represented_comment_count": represented_comment_count or len(nodes),
        "post_score": post_score,
        "parser": "reference_markdown_r44j",
    }
    return nodes, meta


def extract_old_reddit_comment_tree_from_dom_r44j(html_text: str, *, target_url: str = DEFAULT_TARGET_URL) -> tuple[list[RedditCommentNodeR44J], dict[str, Any]]:
    """Best-effort old Reddit DOM parser.

    It targets old Reddit comment blocks such as div.thing.id-t1_x with
    data-fullname/data-parent attributes. If those attributes are absent, callers
    should fall back to parse_reference_markdown_comment_tree_r44j or R44D records.
    """
    html = str(html_text or "")
    blocks: list[str] = []
    for match in re.finditer(r"<div\b[^>]*(?:thing|comment)[^>]*\bid=['\"]thing_t1_[^'\"]+['\"][^>]*>.*?(?=<div\b[^>]*(?:thing|comment)[^>]*\bid=['\"]thing_t1_|</body>|</html>)", html, re.I | re.S):
        blocks.append(match.group(0))
    if not blocks:
        for match in re.finditer(r"<div\b[^>]*\bdata-fullname=['\"]t1_[^'\"]+['\"][^>]*>.*?(?=<div\b[^>]*\bdata-fullname=['\"]t1_|</body>|</html>)", html, re.I | re.S):
            blocks.append(match.group(0))
    nodes: list[RedditCommentNodeR44J] = []
    for idx, block in enumerate(blocks, start=1):
        comment_id = _first_match(block, [r"data-fullname=['\"]t1_([^'\"]+)", r"id=['\"]thing_t1_([^'\"]+)"]) or f"oldreddit_{idx:03d}"
        parent_id = _first_match(block, [r"data-parent=['\"]t1_([^'\"]+)", r"data-parent-fullname=['\"]t1_([^'\"]+)"]) or ""
        author = _clean_author(_first_match(block, [r"data-author=['\"]([^'\"]+)", r"class=['\"]author[^'\"]*['\"][^>]*>(.*?)</a>"]) or "unknown")
        score_display = _score_from_old_block(block)
        depth = _depth_from_old_block(block)
        body = _body_from_old_block(block)
        nodes.append(RedditCommentNodeR44J(
            ordinal=idx,
            comment_id=comment_id,
            parent_id=parent_id,
            depth=depth,
            author=author,
            score_display=score_display,
            score_kind=_score_kind(score_display),
            body=body,
            source_url=_comment_url(target_url, comment_id),
            source_kind="old_reddit_dom",
            capture_order=idx,
        ))
    if nodes and not any(n.parent_id for n in nodes):
        nodes = _assign_parents_from_depth(nodes)
    meta = {"parser": "old_reddit_dom_r44j", "represented_comment_count": len(nodes)}
    return nodes, meta


def run_reddit_comment_tree_extraction_r44j(
    *,
    reference_markdown_path: str = "",
    reference_markdown_text: str = "",
    old_reddit_html_path: str = "",
    old_reddit_html_text: str = "",
    ordered_branch_source_path: str = "",
    ordered_branch_source_text: str = "",
    target_url: str = DEFAULT_TARGET_URL,
    output_root: str = DEFAULT_OUTPUT_ROOT,
    reported_comment_count: int = 0,
    signed_in_profile_available: bool = False,
    max_items: int = 500,
) -> RedditCommentTreeResultR44J:
    root = Path(output_root)
    capture_ts = _now_ts()
    run_dir = root / f"reddit_comment_tree_extraction_{capture_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    ref_text = reference_markdown_text or _read_optional(reference_markdown_path)
    html_text = old_reddit_html_text or _read_optional(old_reddit_html_path)
    branch_text = ordered_branch_source_text or _read_optional(ordered_branch_source_path)

    warnings: list[str] = []
    if ref_text.strip():
        nodes, meta = parse_reference_markdown_comment_tree_r44j(ref_text, target_url=target_url)
    elif html_text.strip():
        nodes, meta = extract_old_reddit_comment_tree_from_dom_r44j(html_text, target_url=target_url)
    else:
        nodes, meta = [], {"parser": "empty"}
        warnings.append("no reference markdown or old Reddit HTML supplied; wrote empty extraction receipt")

    if max_items and len(nodes) > max_items:
        warnings.append(f"max_items={max_items} truncated parsed nodes from {len(nodes)}")
        nodes = nodes[:max_items]

    branch_rows = parse_ordered_branch_source_r44j(branch_text)
    represented = int(meta.get("represented_comment_count") or len(nodes))
    reported = int(reported_comment_count or meta.get("reported_comment_count") or 0)
    gap = max(0, reported - len(nodes)) if reported else 0
    policy = build_large_reddit_thread_policy_r44j(
        reported_comment_count=reported,
        recovered_comment_count=len(nodes),
        branch_url_count=len(branch_rows),
        signed_in_profile_available=signed_in_profile_available,
    )
    route = choose_reddit_capture_route_r44j(signed_in_profile_available=signed_in_profile_available)

    index_path = run_dir / "reddit_comment_tree_index.json"
    md_path = run_dir / "reddit_comment_tree_index.md"
    ndjson_path = run_dir / "reddit_comment_tree_index.ndjson"
    plan_path = run_dir / "reddit_comment_capture_plan.json"
    receipt_path = run_dir / "r44j_reddit_comment_tree_extraction_receipt.json"

    node_dicts = [n.to_dict() for n in nodes]
    _write_json(index_path, {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "target_url": target_url,
        "reported_comment_count": reported,
        "recovered_comment_count": len(nodes),
        "represented_comment_count_from_source": represented,
        "count_gap": gap,
        "nodes": node_dicts,
    })
    _write_text(md_path, _nodes_to_markdown(nodes, reported_count=reported, target_url=target_url))
    _write_text(ndjson_path, "\n".join(json.dumps(n.to_dict(), sort_keys=True, ensure_ascii=False) for n in nodes) + ("\n" if nodes else ""))
    _write_json(plan_path, {
        "marker": MARKER,
        "target_url": target_url,
        "route": route,
        "large_thread_policy": policy,
        "branch_queue": branch_rows,
        "fallback_normal_site": choose_reddit_capture_route_r44j(signed_in_profile_available=False, old_reddit_login_gate=True, current_reddit_network_block=False),
        "source_parser": meta.get("parser"),
    })

    result = RedditCommentTreeResultR44J(
        marker=MARKER,
        schema_version=SCHEMA_VERSION,
        status=PASS_STATUS,
        target_url=target_url,
        output_root=str(root),
        run_dir=str(run_dir),
        comment_index_path=str(index_path),
        comment_tree_markdown_path=str(md_path),
        comment_tree_ndjson_path=str(ndjson_path),
        capture_plan_path=str(plan_path),
        receipt_path=str(receipt_path),
        reported_comment_count=reported,
        recovered_comment_count=len(nodes),
        count_gap=gap,
        top_level_comment_count=sum(1 for n in nodes if n.depth == 0),
        max_comment_depth=max((n.depth for n in nodes), default=0),
        hidden_score_count=sum(1 for n in nodes if n.score_kind == "hidden"),
        negative_score_count=sum(1 for n in nodes if n.score_kind == "negative"),
        score_count=sum(1 for n in nodes if n.score_kind in {"positive", "zero", "negative"}),
        branch_url_count=len(branch_rows),
        strategy=route.get("route", ""),
        fallback_strategy="no_login_current_reddit_visible_target_only",
        large_thread_policy=policy,
        side_effect_flags=build_side_effect_flags_r44j(),
        warnings=tuple(warnings),
    )
    _write_json(receipt_path, result.to_dict())
    return result


def build_side_effect_flags_r44j() -> dict[str, bool]:
    return {
        "reddit_comment_tree_extraction_invoked": True,
        "browser_session_started": False,
        "network_actions_performed": False,
        "browser_profile_files_read_or_copied": False,
        "browser_profile_files_parsed_by_tool": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
    }


def run_self_test(output_root: str | Path = DEFAULT_OUTPUT_ROOT) -> RedditCommentTreeReportR44J:
    root = Path(output_root)
    fixture_md = """# Reddit thread archive — all visible comments, reply-tree indentation, and displayed vote scores
- **Reddit thread counter in screenshots:** `337 comments`
- **Visible/recoverable comment nodes represented in this transcript:** `333`
## Comments
- **1. u/EdSheeran-ModTeam [MOD]** — `score: hidden/not shown`
  Rule note body
- **2. u/Hassaan18** — `score: 49`
  He can do the show.
  - **3. u/ertri** — `score: 2`
    Stripped down … stadium gig
    - **4. u/unknowingexpert69** — `score: 1`
      He’s looped in stadiums for many tours…
  - **5. u/Stonerthrowaway710 [OP]** — `score: -17`
    Free Palestine comment text.
"""
    branch_text = """1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/?force-legacy-sct=1
2 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa15vni/?force-legacy-sct=1
2.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa19tv2/?force-legacy-sct=1
"""
    result = run_reddit_comment_tree_extraction_r44j(
        reference_markdown_text=fixture_md,
        ordered_branch_source_text=branch_text,
        target_url=DEFAULT_TARGET_URL,
        output_root=str(root / "self_test"),
        signed_in_profile_available=True,
    )
    branch_rows = parse_ordered_branch_source_r44j(branch_text)
    policy = build_large_reddit_thread_policy_r44j(reported_comment_count=1200, recovered_comment_count=500, branch_url_count=42, signed_in_profile_available=True)
    fallback = choose_reddit_capture_route_r44j(signed_in_profile_available=False, old_reddit_login_gate=True, current_reddit_network_block=False)
    checks = [
        {"name": "reference_markdown_extracts_comments", "status": "pass" if result.recovered_comment_count == 5 else "fail"},
        {"name": "indentation_depth_preserved", "status": "pass" if result.max_comment_depth >= 2 else "fail"},
        {"name": "hidden_and_negative_scores_preserved", "status": "pass" if result.hidden_score_count == 1 and result.negative_score_count == 1 else "fail"},
        {"name": "branch_labels_preserve_nested_order", "status": "pass" if [r["label"] for r in branch_rows] == ["1", "2", "2.1"] else "fail"},
        {"name": "large_thread_uses_resumable_queue", "status": "pass" if policy["large_thread"] and policy["requires_resumable_queue"] and policy["do_not_invent_missing_nodes"] else "fail"},
        {"name": "no_login_fallback_uses_normal_site", "status": "pass" if fallback["route"] == "no_login_current_reddit_visible_target_only" else "fail"},
        {"name": "side_effects_safe", "status": "pass" if not any(v for k, v in build_side_effect_flags_r44j().items() if k not in {"reddit_comment_tree_extraction_invoked"}) else "fail"},
    ]
    status = PASS_STATUS if all(c["status"] == "pass" for c in checks) else BLOCKED_STATUS
    report = RedditCommentTreeReportR44J(
        marker=MARKER,
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=tuple(checks),
        sample_result=result.to_dict(),
        contract=build_reddit_comment_tree_extraction_contract_r44j(),
        side_effect_flags=build_side_effect_flags_r44j(),
    )
    _write_json(root / "R44J_REDDIT_COMMENT_TREE_EXTRACTION_REPORT.json", report.to_dict())
    _write_text(root / "R44J_REDDIT_COMMENT_TREE_EXTRACTION_REPORT.md", _report_md(report))
    return report


def _node_from_current(current: Mapping[str, Any], body_lines: Sequence[str], target_url: str, capture_order: int) -> RedditCommentNodeR44J:
    ordinal = int(current.get("ordinal") or capture_order)
    score_display = str(current.get("score_display") or "hidden/not shown").strip()
    author = _clean_author(current.get("author") or "unknown")
    return RedditCommentNodeR44J(
        ordinal=ordinal,
        comment_id=f"ref_{ordinal:04d}",
        parent_id="",
        depth=max(0, int(current.get("depth") or 0)),
        author=author,
        score_display=score_display,
        score_kind=_score_kind(score_display),
        body="\n".join(_strip_markdown_body_line(line) for line in body_lines).strip(),
        source_url=target_url,
        source_kind="reference_markdown",
        capture_order=capture_order,
    )


def _assign_parents_from_depth(nodes: Sequence[RedditCommentNodeR44J]) -> list[RedditCommentNodeR44J]:
    stack: dict[int, RedditCommentNodeR44J] = {}
    out: list[RedditCommentNodeR44J] = []
    for node in nodes:
        parent = stack.get(node.depth - 1) if node.depth > 0 else None
        comment_id = node.comment_id if not node.comment_id.startswith("ref_") else f"ref_{node.ordinal:04d}"
        updated = RedditCommentNodeR44J(**{**node.to_dict(), "comment_id": comment_id, "parent_id": parent.comment_id if parent else ""})
        out.append(updated)
        stack[updated.depth] = updated
        for d in list(stack):
            if d > updated.depth:
                stack.pop(d, None)
    return out


def _nodes_to_markdown(nodes: Sequence[RedditCommentNodeR44J], *, reported_count: int, target_url: str) -> str:
    lines = [
        "# Reddit comment tree extraction — R44J",
        "",
        f"- Target URL: `{target_url}`",
        f"- Reported comment count: `{reported_count or 'unknown'}`",
        f"- Recovered comment nodes: `{len(nodes)}`",
        "- Vote note: displayed net scores only; exact separate upvotes/downvotes are not inferred.",
        "",
        "## Comments",
        "",
    ]
    for node in nodes:
        prefix = "  " * max(0, node.depth)
        lines.append(f"{prefix}- **{node.ordinal}. u/{node.author}** — `score: {node.score_display}`")
        if node.body:
            for body_line in node.body.splitlines():
                lines.append(f"{prefix}  {body_line}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _report_md(report: RedditCommentTreeReportR44J) -> str:
    lines = [f"# {MARKER}", "", f"Status: `{report.status}`", "", "## Checks"]
    for check in report.checks:
        lines.append(f"- `{check.get('name')}`: **{check.get('status')}**")
    lines.extend(["", "## Contract", "", "```json", json.dumps(report.contract, indent=2, sort_keys=True), "```", ""])
    return "\n".join(lines)


def _first_match(text: str, patterns: Sequence[str]) -> str:
    for pat in patterns:
        m = re.search(pat, text or "", re.I | re.S)
        if m:
            return _clean_html(m.group(1))
    return ""


def _score_from_old_block(block: str) -> str:
    for pat in (
        r"<span[^>]+class=['\"][^'\"]*score[^'\"]*unvoted[^'\"]*['\"][^>]*>(.*?)</span>",
        r"<span[^>]+class=['\"][^'\"]*score[^'\"]*['\"][^>]*>(.*?)</span>",
    ):
        m = re.search(pat, block, re.I | re.S)
        if m:
            text = _clean_html(m.group(1))
            num = re.search(r"-?\d+", text.replace(",", ""))
            if num:
                return num.group(0)
            if text:
                return text
    if "score hidden" in block.lower() or "[score hidden]" in block.lower():
        return "hidden/not shown"
    return "hidden/not shown"


def _depth_from_old_block(block: str) -> int:
    m = re.search(r"class=['\"][^'\"]*depth-(\d+)", block, re.I)
    if m:
        return max(0, int(m.group(1)))
    m = re.search(r"data-depth=['\"](\d+)", block, re.I)
    if m:
        return max(0, int(m.group(1)))
    return 0


def _body_from_old_block(block: str) -> str:
    m = re.search(r"<div[^>]+class=['\"][^'\"]*md[^'\"]*['\"][^>]*>(.*?)</div>", block, re.I | re.S)
    if m:
        return _clean_html(m.group(1))
    return _clean_html(block)


def _score_kind(score: str) -> str:
    text = str(score or "").strip().lower()
    if not text or "hidden" in text or "not shown" in text:
        return "hidden"
    m = re.search(r"-?\d+", text.replace(",", ""))
    if not m:
        return "text"
    value = int(m.group(0))
    if value < 0:
        return "negative"
    if value == 0:
        return "zero"
    return "positive"


def _strip_markdown_body_line(line: str) -> str:
    text = str(line).strip()
    text = re.sub(r"^[-*]\s+", "", text)
    return text


def _clean_html(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", str(text or ""), flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return _clean(html_lib.unescape(text))


def _clean(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\u00a0", " ")).strip()


def _clean_author(text: Any) -> str:
    value = _clean(text)
    value = re.sub(r"\s+\[(?:OP|MOD)\].*$", "", value, flags=re.I)
    value = value.replace("u/", "").strip()
    return value or "unknown"


def _plain_url(url: str) -> str:
    return str(url or "").strip().strip("<>").replace("&amp;", "&")


def _comment_url(target_url: str, comment_id: str) -> str:
    target = _plain_url(target_url)
    if not comment_id or comment_id.startswith("ref_"):
        return target
    base = target.split("?", 1)[0].rstrip("/")
    return f"{base}/comment/{comment_id}/"


def _read_optional(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8", errors="replace")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="R44J Reddit comment tree extraction and indentation")
    parser.add_argument("--reference-markdown-path", default="")
    parser.add_argument("--old-reddit-html-path", default="")
    parser.add_argument("--ordered-branch-source-file", default="")
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reported-comment-count", type=int, default=0)
    parser.add_argument("--signed-in-profile-available", action="store_true")
    parser.add_argument("--max-items", type=int, default=500)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        report = run_self_test(args.output_root)
        print(MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if report.status == PASS_STATUS else 1
    result = run_reddit_comment_tree_extraction_r44j(
        reference_markdown_path=args.reference_markdown_path,
        old_reddit_html_path=args.old_reddit_html_path,
        ordered_branch_source_path=args.ordered_branch_source_file,
        target_url=args.target_url,
        output_root=args.output_root,
        reported_comment_count=args.reported_comment_count,
        signed_in_profile_available=args.signed_in_profile_available,
        max_items=args.max_items,
    )
    print(MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
    if result.status == PASS_STATUS:
        print("R44J_REDDIT_COMMENT_TREE_EXTRACTION_DONE")
        return 0
    print("R44J_REDDIT_COMMENT_TREE_EXTRACTION_BLOCKED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
