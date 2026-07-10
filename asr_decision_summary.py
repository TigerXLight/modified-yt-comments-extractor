from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from asr_comparison_report import (
    ASR_ENGINE_LOCAL,
    ASR_ENGINE_OFFLINE,
    ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD,
    ASR_RESULT_SOURCE_USER_OBSERVATION,
    ASR_STATUS_ACCEPTED,
    ASR_STATUS_BLOCKED,
    ASR_STATUS_CANDIDATE,
    ASR_STATUS_NEEDS_REVIEW,
    ASR_STATUS_REJECTED,
    ASR_STATUS_UNKNOWN,
    ASRComparisonRecord,
    rank_asr_records,
)


DEFAULT_PROJECT_THRESHOLD_PERCENT = 95.0
EXTERNAL_LEAD_SOURCES = (
    ASR_RESULT_SOURCE_EXTERNAL_LEADERBOARD,
    ASR_RESULT_SOURCE_USER_OBSERVATION,
)


@dataclass(frozen=True)
class ASRDecisionSummaryResult:
    threshold_percent: float = DEFAULT_PROJECT_THRESHOLD_PERCENT
    record_count: int = 0
    project_scored_count: int = 0
    accepted_count: int = 0
    candidate_count: int = 0
    rejected_count: int = 0
    blocked_count: int = 0
    needs_review_count: int = 0
    unknown_count: int = 0
    external_lead_count: int = 0
    best_scored_label: str = ""
    best_scored_accuracy_percent: float | None = None
    best_local_label: str = ""
    best_local_accuracy_percent: float | None = None
    below_threshold_count: int = 0
    blocked_labels: tuple[str, ...] = ()
    blocked_details: tuple[str, ...] = ()
    below_threshold_candidate_labels: tuple[str, ...] = ()
    recommendation: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _label(record: ASRComparisonRecord) -> str:
    provider = record.provider or "(unknown provider)"
    return f"{provider} / {record.model}" if record.model else provider


def _status_count(records: Sequence[ASRComparisonRecord], status: str) -> int:
    return sum(record.status == status for record in records)


def _best_record(records: Sequence[ASRComparisonRecord]) -> ASRComparisonRecord | None:
    return rank_asr_records(records, metric="reference_accuracy_percent")[0] if records else None


def _recommendation(
    *,
    accepted_count: int,
    best_scored: ASRComparisonRecord | None,
    best_local: ASRComparisonRecord | None,
    threshold_percent: float,
) -> str:
    if accepted_count:
        return (
            "Keep accepted results subject to explicit user review and Term QA; verify that each "
            "accepted status is backed by project-specific scoring at or above the current gate."
        )
    best_text = _label(best_scored) if best_scored else "the current leading scored result"
    local_text = _label(best_local) if best_local else "the current local/offline fallback"
    return (
        f"Keep ASR output as draft text. Treat {best_text} as a candidate rather than accepted, "
        f"retain {local_text} for local/offline use where appropriate, and require explicit Term QA "
        f"and user review before integration because no project-scored result reaches {threshold_percent:.2f}%."
    )


def build_asr_decision_summary(
    records: Sequence[ASRComparisonRecord],
    *,
    threshold_percent: float = DEFAULT_PROJECT_THRESHOLD_PERCENT,
) -> ASRDecisionSummaryResult:
    record_tuple = tuple(records)
    project_scored = tuple(
        record
        for record in record_tuple
        if record.has_local_reference_evidence and record.status != ASR_STATUS_BLOCKED
    )
    local_scored = tuple(
        record
        for record in project_scored
        if record.engine_type in {ASR_ENGINE_LOCAL, ASR_ENGINE_OFFLINE}
    )
    best_scored = _best_record(project_scored)
    best_local = _best_record(local_scored)
    blocked = tuple(record for record in record_tuple if record.status == ASR_STATUS_BLOCKED)
    below_threshold = tuple(
        record
        for record in project_scored
        if record.reference_accuracy_percent is not None
        and record.reference_accuracy_percent < threshold_percent
    )
    below_threshold_candidates = tuple(
        record for record in below_threshold if record.status == ASR_STATUS_CANDIDATE
    )
    external_leads = tuple(
        record for record in record_tuple if record.source in EXTERNAL_LEAD_SOURCES
    )
    accepted_count = _status_count(record_tuple, ASR_STATUS_ACCEPTED)

    warnings: list[str] = []
    if accepted_count == 0:
        warnings.append("No ASR provider/model is marked accepted in the supplied records.")
    if below_threshold:
        warnings.append(
            f"All {len(below_threshold)} project-scored result(s) below {threshold_percent:.2f}% remain draft/not final truth."
        )
    if below_threshold_candidates:
        warnings.append(
            "Candidate status does not imply acceptance; below-threshold candidates still require Term QA and user review."
        )
    if blocked:
        warnings.append(
            "Blocked providers have no comparable quality result and must not be ranked as quality-rejected."
        )
    if external_leads:
        warnings.append(
            "External leaderboard and user-observation leads are informational only and are not accepted providers."
        )

    errors: list[str] = []
    for record in record_tuple:
        if record.status != ASR_STATUS_ACCEPTED:
            continue
        if not record.has_local_reference_evidence:
            errors.append(
                f"Accepted record lacks project-specific reference evidence: {_label(record)}"
            )
        elif (
            record.reference_accuracy_percent is not None
            and record.reference_accuracy_percent < threshold_percent
        ):
            errors.append(
                f"Accepted record is below the {threshold_percent:.2f}% gate: {_label(record)}"
            )

    return ASRDecisionSummaryResult(
        threshold_percent=threshold_percent,
        record_count=len(record_tuple),
        project_scored_count=len(project_scored),
        accepted_count=accepted_count,
        candidate_count=_status_count(record_tuple, ASR_STATUS_CANDIDATE),
        rejected_count=_status_count(record_tuple, ASR_STATUS_REJECTED),
        blocked_count=len(blocked),
        needs_review_count=_status_count(record_tuple, ASR_STATUS_NEEDS_REVIEW),
        unknown_count=_status_count(record_tuple, ASR_STATUS_UNKNOWN),
        external_lead_count=len(external_leads),
        best_scored_label=_label(best_scored) if best_scored else "",
        best_scored_accuracy_percent=(
            best_scored.reference_accuracy_percent if best_scored else None
        ),
        best_local_label=_label(best_local) if best_local else "",
        best_local_accuracy_percent=(
            best_local.reference_accuracy_percent if best_local else None
        ),
        below_threshold_count=len(below_threshold),
        blocked_labels=tuple(_label(record) for record in blocked),
        blocked_details=tuple(
            f"{_label(record)}: {record.notes or 'No quality score was produced.'}"
            for record in blocked
        ),
        below_threshold_candidate_labels=tuple(
            _label(record) for record in below_threshold_candidates
        ),
        recommendation=_recommendation(
            accepted_count=accepted_count,
            best_scored=best_scored,
            best_local=best_local,
            threshold_percent=threshold_percent,
        ),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def asr_decision_summary_to_dict(
    result: ASRDecisionSummaryResult,
) -> dict[str, object]:
    return {
        "accepted_count": result.accepted_count,
        "below_threshold_candidate_labels": list(result.below_threshold_candidate_labels),
        "below_threshold_count": result.below_threshold_count,
        "best_local_accuracy_percent": result.best_local_accuracy_percent,
        "best_local_label": result.best_local_label,
        "best_scored_accuracy_percent": result.best_scored_accuracy_percent,
        "best_scored_label": result.best_scored_label,
        "blocked_count": result.blocked_count,
        "blocked_details": list(result.blocked_details),
        "blocked_labels": list(result.blocked_labels),
        "candidate_count": result.candidate_count,
        "errors": list(result.errors),
        "external_lead_count": result.external_lead_count,
        "needs_review_count": result.needs_review_count,
        "project_scored_count": result.project_scored_count,
        "recommendation": result.recommendation,
        "record_count": result.record_count,
        "rejected_count": result.rejected_count,
        "threshold_percent": result.threshold_percent,
        "unknown_count": result.unknown_count,
        "warnings": list(result.warnings),
    }


def _percent(value: float | None) -> str:
    return "(none)" if value is None else f"{value:.2f}%"


def _list_lines(values: Sequence[str]) -> list[str]:
    return [f"- {value}" for value in values] if values else ["- (none)"]


def build_asr_decision_summary_text(result: ASRDecisionSummaryResult) -> str:
    lines = [
        "ASR decision summary",
        "Scope: local/manual comparison records only; no provider calls or transcription are performed.",
        f"Strict project threshold: {result.threshold_percent:.2f}%",
        f"Record count: {result.record_count}",
        f"Project-scored count: {result.project_scored_count}",
        f"Accepted count: {result.accepted_count}",
        f"Candidate count: {result.candidate_count}",
        f"Rejected count: {result.rejected_count}",
        f"Blocked count: {result.blocked_count}",
        f"Needs-review count: {result.needs_review_count}",
        f"External-lead count: {result.external_lead_count}",
        f"Below-threshold project-scored count: {result.below_threshold_count}",
        f"Best project-scored result: {result.best_scored_label or '(none)'} [{_percent(result.best_scored_accuracy_percent)}]",
        f"Best local/offline result: {result.best_local_label or '(none)'} [{_percent(result.best_local_accuracy_percent)}]",
        "Blocked providers/items:",
        *_list_lines(result.blocked_details),
        "Below-threshold candidates:",
        *_list_lines(result.below_threshold_candidate_labels),
        "Warnings:",
        *_list_lines(result.warnings),
        "Errors:",
        *_list_lines(result.errors),
        f"Safe next action: {result.recommendation}",
    ]
    return "\n".join(lines)


def build_asr_decision_summary_markdown(result: ASRDecisionSummaryResult) -> str:
    lines = [
        "# ASR Decision Summary",
        "",
        "Local/manual comparison records only. This report does not call providers, run transcription, download/fetch media, use network APIs, store credentials, or wire into the GUI.",
        "",
        "## Decision Counts",
        "",
        f"- Strict project threshold: {result.threshold_percent:.2f}%",
        f"- Record count: {result.record_count}",
        f"- Project-scored count: {result.project_scored_count}",
        f"- Accepted: {result.accepted_count}",
        f"- Candidate: {result.candidate_count}",
        f"- Rejected: {result.rejected_count}",
        f"- Blocked: {result.blocked_count}",
        f"- Needs review: {result.needs_review_count}",
        f"- External/user-observation leads: {result.external_lead_count}",
        f"- Below-threshold project-scored: {result.below_threshold_count}",
        "",
        "## Leading Scored Results",
        "",
        f"- Best project-scored result: {result.best_scored_label or '(none)'} ({_percent(result.best_scored_accuracy_percent)}).",
        f"- Best local/offline result: {result.best_local_label or '(none)'} ({_percent(result.best_local_accuracy_percent)}).",
        "",
        "## Blocked Providers",
        "",
        *_list_lines(result.blocked_details),
        "",
        "Blocked means no comparable quality score was produced; it is not a quality rejection.",
        "",
        "## Below-Threshold Candidates",
        "",
        *_list_lines(result.below_threshold_candidate_labels),
        "",
        "Candidate means worth considering or retesting, not accepted.",
        "",
        "## Warnings",
        "",
        *_list_lines(result.warnings),
        "",
        "## Safe Next Action",
        "",
        result.recommendation,
        "",
        "External leaderboard/research leads do not override project-specific strict scoring or Term QA.",
    ]
    if result.errors:
        lines.extend(["", "## Errors", "", *_list_lines(result.errors)])
    return "\n".join(lines)
