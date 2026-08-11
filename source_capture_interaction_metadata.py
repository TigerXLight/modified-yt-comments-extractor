from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACCEPTED_ARTICLE_SCREENSHOT = "android_article_MAIN_SINGLE_reference_style.png"
ACCEPTED_COMMENTS_SCREENSHOT = "android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png"
PREFERRED_REPLAY_SCREENSHOT = "Corrected full-page.png"
DIAGNOSTIC_REPLAY_SCREENSHOTS = {"full-page.png", "article-top.png", "comments-region.png", "full-comments-thread.png"}


@dataclass
class InteractionStep:
    step_id: str
    action: str
    target: str
    purpose: str
    status: str
    evidence_paths: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class ResourceReceipt:
    category: str
    relative_path: str
    absolute_path: str
    size_bytes: int
    sha256: str


@dataclass
class ScreenshotEvidence:
    role: str
    path: str
    sha256: str
    size_bytes: int
    status: str
    note: str = ""


@dataclass
class CaptureInteractionMetadata:
    target_url: str
    normalized_target_url: str
    generated_at_utc: str
    status: str
    interaction_policy: str
    capture_roots: list[str]
    production_roots: list[str]
    steps: list[InteractionStep] = field(default_factory=list)
    accepted_primary_screenshots: list[ScreenshotEvidence] = field(default_factory=list)
    preferred_replay_reference_screenshots: list[ScreenshotEvidence] = field(default_factory=list)
    diagnostic_screenshots: list[ScreenshotEvidence] = field(default_factory=list)
    replay_artifacts: list[ResourceReceipt] = field(default_factory=list)
    resource_inventory: list[ResourceReceipt] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def safe_relative(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return path.name


def classify_resource(path: Path) -> str:
    name = path.name
    lower = name.lower()
    rel_lower = str(path).lower()
    if lower == ACCEPTED_ARTICLE_SCREENSHOT.lower() or lower == ACCEPTED_COMMENTS_SCREENSHOT.lower():
        return "accepted_primary_screenshot"
    if lower == PREFERRED_REPLAY_SCREENSHOT.lower():
        return "preferred_replay_reference_screenshot"
    if lower in {item.lower() for item in DIAGNOSTIC_REPLAY_SCREENSHOTS}:
        return "diagnostic_replay_screenshot"
    if lower.endswith(".wacz"):
        return "wacz_replay_candidate"
    if lower.endswith(".warc.gz") or lower.endswith(".warc"):
        return "warc_replay_candidate"
    if lower == "rendered-page.html":
        return "rendered_html_replay_candidate"
    if lower in {"comments.json", "comments.txt", "comments.html", "comments.md", "profiles.json", "profiles.txt"}:
        return "structured_export"
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")):
        return "image_or_screenshot"
    if "local_viewer" in rel_lower:
        return "local_viewer_manifest"
    if lower.endswith((".json", ".jsonl", ".txt", ".html", ".md")):
        return "supporting_metadata"
    return "supporting_resource"


def make_receipt(path: Path, roots: list[Path]) -> ResourceReceipt:
    return ResourceReceipt(
        category=classify_resource(path),
        relative_path=safe_relative(path, roots),
        absolute_path=str(path),
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
    )


def scan_files(roots: list[Path]) -> list[ResourceReceipt]:
    existing_roots = [root for root in roots if root.exists()]
    receipts: list[ResourceReceipt] = []
    for root in existing_roots:
        if root.is_file():
            receipts.append(make_receipt(root, existing_roots))
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                receipts.append(make_receipt(path, existing_roots))
    seen: set[str] = set()
    unique: list[ResourceReceipt] = []
    for item in receipts:
        key = item.absolute_path.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def evidence_from_receipt(receipt: ResourceReceipt, *, status: str, role: str, note: str = "") -> ScreenshotEvidence:
    return ScreenshotEvidence(role=role, path=receipt.absolute_path, sha256=receipt.sha256, size_bytes=receipt.size_bytes, status=status, note=note)


def _receipt_paths(receipts: list[ResourceReceipt], *names: str, contains: str = "") -> list[str]:
    wanted = {name.lower() for name in names}
    out = []
    for receipt in receipts:
        name_match = Path(receipt.absolute_path).name.lower() in wanted if wanted else False
        contains_match = contains.lower() in receipt.relative_path.lower() if contains else False
        if name_match or contains_match:
            out.append(receipt.absolute_path)
    return out


def _action_log_text(receipts: list[ResourceReceipt]) -> str:
    chunks: list[str] = []
    for receipt in receipts:
        if Path(receipt.absolute_path).name.lower() == "action_log.jsonl":
            try:
                chunks.append(Path(receipt.absolute_path).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return "\n".join(chunks).lower()


def _step(step_id: str, action: str, target: str, purpose: str, evidence_paths: list[str], *, inferred: bool = False, note: str = "") -> InteractionStep:
    if evidence_paths and inferred:
        status = "INFERRED_FROM_ARTIFACTS"
    elif evidence_paths:
        status = "RECORDED"
    else:
        status = "MISSING_OR_NOT_FOUND"
    return InteractionStep(step_id=step_id, action=action, target=target, purpose=purpose, status=status, evidence_paths=evidence_paths[:8], note=note)


def build_steps(receipts: list[ResourceReceipt]) -> list[InteractionStep]:
    action_text = _action_log_text(receipts)
    article_evidence = _receipt_paths(receipts, "article.txt", "final_rendered_dom.html", "rendered-page.html")
    comment_evidence = _receipt_paths(receipts, "comments.json", "comments.txt", "comments_incremental.jsonl", "comments_provider_reconciliation.json")
    accepted_article = _receipt_paths(receipts, ACCEPTED_ARTICLE_SCREENSHOT)
    accepted_comments = _receipt_paths(receipts, ACCEPTED_COMMENTS_SCREENSHOT)
    warc_evidence = [r.absolute_path for r in receipts if r.category in {"warc_replay_candidate", "wacz_replay_candidate", "rendered_html_replay_candidate"}]
    export_evidence = [r.absolute_path for r in receipts if r.category == "structured_export"]
    shadow_evidence = _receipt_paths(receipts, "comments_derived_layout_transformations.json", contains="social-comment-wc")
    scroll_evidence = _receipt_paths(receipts, "faithful_full_page.png", "full-page.png", PREFERRED_REPLAY_SCREENSHOT)
    if "scroll" in action_text:
        scroll_evidence += _receipt_paths(receipts, "action_log.jsonl")
    expand_reply_evidence = _receipt_paths(receipts, "comments_incremental.jsonl", "comments_provider_reconciliation.json")
    if "expand" in action_text or "reply" in action_text:
        expand_reply_evidence += _receipt_paths(receipts, "action_log.jsonl")
    expand_text_evidence = _receipt_paths(receipts, "comments_derived_layout_transformations.json")
    if "see more" in action_text or "clamp" in action_text:
        expand_text_evidence += _receipt_paths(receipts, "action_log.jsonl")
    consent_evidence = _receipt_paths(receipts, "validation.json", "rendered_validation_summary.json", ACCEPTED_ARTICLE_SCREENSHOT, ACCEPTED_COMMENTS_SCREENSHOT)
    return [
        _step("open_article", "open", "MSN article URL", "Load article shell and article payload.", article_evidence),
        _step("wait_render", "wait", "article web components", "Allow dynamic MSN article components to render.", _receipt_paths(receipts, "final_rendered_dom.html", "rendered-page.html")),
        _step("scroll_article", "scroll", "article page", "Trigger lazy images/footer/resources.", scroll_evidence, inferred="scroll" not in action_text),
        _step("open_comments", "navigate/click", "#comments / social-comment-wc", "Open comments overlay when comment preservation is requested.", comment_evidence, inferred="comments" not in action_text),
        _step("shadow_dom_comments", "inspect", "open shadow roots", "Locate internal comments scroller.", shadow_evidence, inferred=True),
        _step("scroll_internal_comments", "scroll", "internal comments scroller", "Load all visible comments/replies.", comment_evidence + accepted_comments, inferred=True),
        _step("expand_replies", "click", "reply expand controls", "Expose collapsed reply threads.", expand_reply_evidence, inferred=True),
        _step("expand_text", "click", "see-more/clamped text controls", "Expose truncated comments.", expand_text_evidence, inferred=True),
        _step("suppress_consent_for_capture", "suppress", "cookie/privacy overlays", "Prevent overlays from hiding final evidence screenshots.", consent_evidence, inferred=True),
        _step("capture_primary_article_screenshot", "screenshot", "article viewport", "Accepted V6-style article evidence.", accepted_article),
        _step("capture_primary_comments_screenshot", "screenshot", "comments internal stitch", "Accepted V15-style comments evidence.", accepted_comments),
        _step("write_archive_files", "write", "rendered HTML / WARC.GZ / WACZ", "Create replay candidates after browser-state capture.", warc_evidence),
        _step("write_exports", "write", "comments/profile/source-role/media-chain exports", "Preserve structured evidence separately from dynamic replay.", export_evidence),
    ]


def build_interaction_metadata(
    *,
    target_url: str,
    normalized_target_url: str,
    capture_roots: list[str] | None = None,
    production_roots: list[str] | None = None,
) -> CaptureInteractionMetadata:
    capture_root_paths = [Path(p) for p in (capture_roots or []) if p]
    production_root_paths = [Path(p) for p in (production_roots or []) if p]
    all_roots = capture_root_paths + production_root_paths
    receipts = scan_files(all_roots)
    accepted: list[ScreenshotEvidence] = []
    preferred: list[ScreenshotEvidence] = []
    diagnostic: list[ScreenshotEvidence] = []
    replay: list[ResourceReceipt] = []
    warnings: list[str] = []
    for item in receipts:
        name = Path(item.absolute_path).name
        if name == ACCEPTED_ARTICLE_SCREENSHOT:
            accepted.append(evidence_from_receipt(item, status="ACCEPTED_PRIMARY_ARTICLE_SCREENSHOT", role="article_primary"))
        elif name == ACCEPTED_COMMENTS_SCREENSHOT:
            accepted.append(evidence_from_receipt(item, status="ACCEPTED_PRIMARY_COMMENTS_SCREENSHOT", role="comments_primary"))
        elif name == PREFERRED_REPLAY_SCREENSHOT:
            preferred.append(evidence_from_receipt(item, status="PREFERRED_REPLAY_REFERENCE", role="replay_reference"))
        elif name in DIAGNOSTIC_REPLAY_SCREENSHOTS:
            diagnostic.append(evidence_from_receipt(item, status="DIAGNOSTIC_ONLY", role="diagnostic_replay", note="diagnostic/review only; not accepted primary screenshot evidence"))
        if item.category in {"warc_replay_candidate", "wacz_replay_candidate", "rendered_html_replay_candidate"}:
            replay.append(item)
    if not any(item.status == "ACCEPTED_PRIMARY_ARTICLE_SCREENSHOT" for item in accepted):
        warnings.append(f"Accepted article screenshot not found: {ACCEPTED_ARTICLE_SCREENSHOT}")
    if not any(item.status == "ACCEPTED_PRIMARY_COMMENTS_SCREENSHOT" for item in accepted):
        warnings.append(f"Accepted comments screenshot not found: {ACCEPTED_COMMENTS_SCREENSHOT}")
    steps = build_steps(receipts)
    status = "RECORDED_WITH_PRIMARY_SCREENSHOTS" if len(accepted) >= 2 else "RECORDED_REVIEW_REQUIRED"
    return CaptureInteractionMetadata(
        target_url=target_url,
        normalized_target_url=normalized_target_url,
        generated_at_utc=utc_now_iso(),
        status=status,
        interaction_policy="Record browser state after relevant actions; mark each step RECORDED/INFERRED/MISSING from concrete artifacts, not roadmap text.",
        capture_roots=[str(p) for p in capture_root_paths],
        production_roots=[str(p) for p in production_root_paths],
        steps=steps,
        accepted_primary_screenshots=accepted,
        preferred_replay_reference_screenshots=preferred,
        diagnostic_screenshots=diagnostic,
        replay_artifacts=replay,
        resource_inventory=receipts,
        limitations=[
            "This records artifact-backed interaction metadata; it does not by itself prove ReplayWeb/pywb visual success.",
            "Comments runtime replay inside WARC/WACZ is not required when comments are preserved separately through structured exports and stitched screenshots.",
            "Old WARCreate extension code is not used as a dependency; the implemented current feature is interaction-before-capture metadata and resource inventory.",
        ],
        warnings=warnings,
    )


def metadata_to_dict(metadata: CaptureInteractionMetadata) -> dict[str, Any]:
    return asdict(metadata)


def metadata_to_text(metadata: CaptureInteractionMetadata) -> str:
    lines: list[str] = []
    lines.append("WARCREATE-STYLE BROWSER INTERACTION METADATA")
    lines.append(f"target_url: {metadata.normalized_target_url}")
    lines.append(f"generated_at_utc: {metadata.generated_at_utc}")
    lines.append(f"status: {metadata.status}")
    lines.append(f"interaction_policy: {metadata.interaction_policy}")
    lines.append("")
    lines.append("STEPS:")
    for step in metadata.steps:
        lines.append(f"  - {step.step_id}: {step.action} -> {step.target}; status={step.status}; purpose={step.purpose}")
        if step.evidence_paths:
            for evidence_path in step.evidence_paths[:4]:
                lines.append(f"      evidence: {evidence_path}")
        if step.note:
            lines.append(f"      note: {step.note}")
    lines.append("")
    lines.append("ACCEPTED_PRIMARY_SCREENSHOTS:")
    if metadata.accepted_primary_screenshots:
        for item in metadata.accepted_primary_screenshots:
            lines.append(f"  - {item.role} | {item.status} | {item.size_bytes} bytes | {item.sha256} | {item.path}")
    else:
        lines.append("  - NONE")
    lines.append("")
    lines.append("PREFERRED_REPLAY_REFERENCE_SCREENSHOTS:")
    if metadata.preferred_replay_reference_screenshots:
        for item in metadata.preferred_replay_reference_screenshots:
            lines.append(f"  - {item.role} | {item.status} | {item.size_bytes} bytes | {item.sha256} | {item.path}")
    else:
        lines.append("  - NONE")
    lines.append("")
    lines.append("DIAGNOSTIC_SCREENSHOTS:")
    if metadata.diagnostic_screenshots:
        for item in metadata.diagnostic_screenshots:
            lines.append(f"  - {item.path}")
    else:
        lines.append("  - NONE")
    lines.append("")
    lines.append("REPLAY_ARTIFACTS:")
    if metadata.replay_artifacts:
        for item in metadata.replay_artifacts:
            lines.append(f"  - {item.category} | {item.relative_path} | {item.size_bytes} bytes | {item.sha256}")
    else:
        lines.append("  - NONE")
    lines.append("")
    lines.append("WARNINGS:")
    if metadata.warnings:
        for warning in metadata.warnings:
            lines.append(f"  - {warning}")
    else:
        lines.append("  - NONE")
    lines.append("")
    lines.append("LIMITATIONS:")
    for limitation in metadata.limitations:
        lines.append(f"  - {limitation}")
    lines.append("")
    lines.append("RESOURCE_INVENTORY:")
    for item in metadata.resource_inventory:
        lines.append(f"  - {item.category} | {item.relative_path} | {item.size_bytes} bytes | {item.sha256}")
    return "\n".join(lines) + "\n"


def write_interaction_sidecars(metadata: CaptureInteractionMetadata, output_dir: str | Path) -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "warcreate_style_interaction_metadata.json"
    txt_path = out / "warcreate_style_interaction_metadata.txt"
    json_path.write_text(json.dumps(metadata_to_dict(metadata), indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text(metadata_to_text(metadata), encoding="utf-8")
    return json_path, txt_path
