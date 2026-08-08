from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from capture_article import extract_article_text_from_html
from capture_comments import extract_comments_from_html_sequence
from capture_livechat import extract_livechat_events_from_html
from capture_page_outline import build_page_outline_from_html


SOURCE_FIXTURE_CAPTURE_RESULTS_SCHEMA_VERSION = "source_fixture_capture_results_v1"


class ScreenshotFidelity(str, Enum):
    FAITHFUL_VIEWPORT = "faithful_viewport"
    FAITHFUL_FULL_PAGE = "faithful_full_page"
    FAITHFUL_ELEMENT_VISIBLE = "faithful_element_visible"
    DERIVED_EXPANDED_STITCHED = "derived_expanded_stitched"
    PRINT_PREPARATION_DOM_MODIFIED = "print_preparation_dom_modified"
    PROTECTED_BLACK_FRAME_BLOCKED = "protected_black_frame_blocked"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(data), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if str(value)}))


@dataclass(frozen=True)
class ScreenshotCaptureContractResult:
    screenshot_id: str
    fidelity: ScreenshotFidelity
    source_url: str
    container_selector: str = ""
    derived_modifications: tuple[str, ...] = ()
    protected_output_blocked: bool = False
    labelled_faithful: bool = False
    artifact_reference: str = ""
    status: str = "fixture_tested"

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["derived_label_guard_ok"] = not (
            self.derived_modifications and self.labelled_faithful
        )
        return data


@dataclass(frozen=True)
class EncodedPayloadCaptureResult:
    payload_id: str
    source: str
    capture_route: str
    decoded_by_page: bool
    encrypted_or_inaccessible: bool = False
    keys_invented_or_bypassed: bool = False
    status: str = "fixture_tested"
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ChallengeContinuationState:
    challenge_id: str
    state: str
    headed_browser_required: bool = True
    user_manual_completion_required: bool = True
    token_stored: bool = False
    privacy_pass_metadata_only: bool = True
    manual_import_fallback_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class VirtualizedCommentCheckpoint:
    checkpoint_id: str
    observed_comment_ids: tuple[str, ...]
    tombstoned_comment_ids: tuple[str, ...] = ()
    first_seen_last_seen_recorded: bool = True
    stable_permalink_preferred: bool = True
    conservative_fingerprint_fallback: bool = True
    scroll_state_checkpointed: bool = True
    stop_condition: str = "fixture_scroll_sequence_exhausted"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class FixtureCaptureResultBundle:
    bundle_id: str
    source_url: str
    article_result: Mapping[str, Any]
    page_outline_result: Mapping[str, Any]
    screenshot_results: tuple[ScreenshotCaptureContractResult, ...]
    comments_result: Mapping[str, Any]
    virtualized_comment_checkpoint: VirtualizedCommentCheckpoint
    encoded_payload_results: tuple[EncodedPayloadCaptureResult, ...]
    challenge_states: tuple[ChallengeContinuationState, ...]
    livechat_result: Mapping[str, Any]
    no_live_execution: bool = True
    browser_automation_performed: bool = False
    screenshots_taken: bool = False
    credentials_stored: bool = False
    schema_version: str = SOURCE_FIXTURE_CAPTURE_RESULTS_SCHEMA_VERSION

    @property
    def screenshot_result_count(self) -> int:
        return len(self.screenshot_results)

    @property
    def comment_count(self) -> int:
        return int(self.comments_result.get("comment_count", len(self.comments_result.get("comments", []))))

    @property
    def livechat_event_count(self) -> int:
        return int(self.livechat_result.get("event_count", len(self.livechat_result.get("events", []))))

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["screenshot_result_count"] = self.screenshot_result_count
        data["comment_count"] = self.comment_count
        data["livechat_event_count"] = self.livechat_event_count
        return data


def build_fixture_capture_result_bundle(
    *,
    source_url: str = "https://example.invalid/source",
    html: str | None = None,
) -> FixtureCaptureResultBundle:
    fixture_html = html or """
    <html>
      <head><title>Fixture Article</title><meta property="og:image" content="/hero.jpg"></head>
      <body>
        <header><nav>Home Links</nav></header>
        <main>
          <article>
            <h1>Fixture Headline</h1>
            <p class="byline">By Fixture Reporter</p>
            <p>First article paragraph with substantial text for density scoring.</p>
            <blockquote>Quoted material remains separate.</blockquote>
            <figure><img src="/image.jpg" alt="Image alt"><figcaption>Fixture caption</figcaption></figure>
          </article>
          <section id="comments" data-load-more="true" data-shadow="open" data-scroll-container="true">
            <div data-comment-id="c1" data-author="Alice" data-source-order="1">First comment</div>
            <div data-comment-id="c2" data-author="Bob" data-parent-id="c1" data-depth="1" data-source-order="2">Reply comment</div>
          </section>
          <section data-virtualized="true" data-disappearing="true" data-stop="fixture_complete">
            <div data-comment-id="v1" data-author="Virtual 1" data-source-order="3">Virtual row one</div>
            <div data-comment-id="v2" data-author="Virtual 2" data-source-order="4">Virtual row two</div>
          </section>
          <div data-event-id="l1" data-author="Chat A" data-timestamp="00:01">hello</div>
          <div data-event-id="l2" data-author="Chat B" data-timestamp="00:02" data-removed="true">removed</div>
        </main>
        <footer>Footer links</footer>
      </body>
    </html>
    """
    article = extract_article_text_from_html(fixture_html, source_url=source_url).to_dict()
    outline = build_page_outline_from_html(fixture_html, source_url=source_url).to_dict()
    comments = extract_comments_from_html_sequence(
        (fixture_html, fixture_html.replace("Virtual row one", "Virtual row one changed")),
        source_url=source_url,
    ).to_dict()
    livechat = extract_livechat_events_from_html(
        fixture_html,
        source_url=source_url,
        message_limit=10,
        duration_limit_seconds=30,
        screenshot_frames=(),
    ).to_dict()
    screenshots = (
        ScreenshotCaptureContractResult(
            screenshot_id="screenshot_viewport_" + _sha16(source_url),
            fidelity=ScreenshotFidelity.FAITHFUL_VIEWPORT,
            source_url=source_url,
            labelled_faithful=True,
            artifact_reference="artifact:faithful_viewport",
        ),
        ScreenshotCaptureContractResult(
            screenshot_id="screenshot_derived_" + _sha16((source_url, "derived")),
            fidelity=ScreenshotFidelity.DERIVED_EXPANDED_STITCHED,
            source_url=source_url,
            derived_modifications=("expanded_scroll_container", "stitched_viewports"),
            labelled_faithful=False,
            artifact_reference="artifact:derived_stitched",
        ),
        ScreenshotCaptureContractResult(
            screenshot_id="screenshot_protected_" + _sha16((source_url, "protected")),
            fidelity=ScreenshotFidelity.PROTECTED_BLACK_FRAME_BLOCKED,
            source_url=source_url,
            protected_output_blocked=True,
            artifact_reference="artifact:protected_blocked_metadata",
            status="blocked",
        ),
    )
    bundle = FixtureCaptureResultBundle(
        bundle_id="fixture_capture_results_" + _sha16((source_url, article, outline, comments, livechat)),
        source_url=source_url,
        article_result=article,
        page_outline_result=outline,
        screenshot_results=screenshots,
        comments_result=comments,
        virtualized_comment_checkpoint=VirtualizedCommentCheckpoint(
            checkpoint_id="virtualized_checkpoint_" + _sha16(comments),
            observed_comment_ids=_dedupe(
                comment.get("comment_id", "") for comment in comments.get("comments", [])
            ),
            tombstoned_comment_ids=("c_deleted_fixture",),
        ),
        encoded_payload_results=(
            EncodedPayloadCaptureResult(
                payload_id="payload_initial_state",
                source="embedded_initial_state",
                capture_route="page_decoded_application_state",
                decoded_by_page=True,
            ),
            EncodedPayloadCaptureResult(
                payload_id="payload_encrypted_blocked",
                source="encrypted_payload_fixture",
                capture_route="blocked_metadata_only",
                decoded_by_page=False,
                encrypted_or_inaccessible=True,
                warning="Payload inaccessible without bypass; no keys invented.",
            ),
        ),
        challenge_states=(
            ChallengeContinuationState(
                challenge_id="challenge_login_required",
                state="capture_paused",
            ),
            ChallengeContinuationState(
                challenge_id="challenge_manual_resume",
                state="resume_requested_after_manual_completion",
            ),
        ),
        livechat_result=livechat,
    )
    return bundle


def validate_fixture_capture_result_bundle(bundle: FixtureCaptureResultBundle | Mapping[str, Any]) -> tuple[str, ...]:
    data = bundle.to_dict() if hasattr(bundle, "to_dict") else dict(bundle)
    errors: list[str] = []
    if not data.get("no_live_execution", False):
        errors.append("no_live_execution_must_be_true")
    if data.get("browser_automation_performed", False):
        errors.append("browser_automation_not_allowed")
    if data.get("screenshots_taken", False):
        errors.append("real_screenshot_capture_not_allowed")
    if data.get("credentials_stored", False):
        errors.append("credentials_must_not_be_stored")
    for screenshot in data.get("screenshot_results", []):
        if screenshot.get("derived_modifications") and screenshot.get("labelled_faithful"):
            errors.append("derived_screenshot_labelled_faithful")
    for challenge in data.get("challenge_states", []):
        if challenge.get("token_stored", False):
            errors.append("challenge_token_stored")
    for payload in data.get("encoded_payload_results", []):
        if payload.get("keys_invented_or_bypassed", False):
            errors.append("encoded_payload_bypass_not_allowed")
    return tuple(errors)


def source_fixture_capture_result_bundle_to_json(bundle: FixtureCaptureResultBundle) -> str:
    return _stable_json(bundle.to_dict(), pretty=True)
