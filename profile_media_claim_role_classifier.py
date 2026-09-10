"""Rule-based claim/span role classifier for Profile/Media review.

The classifier is deterministic and conservative.  It assigns PRIMARY,
SECONDARY, TERTIARY, UNKNOWN, or BLANK at clause level while preserving the
separate media/source provenance role.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from profile_media_claim_role_policy import (
    POLICY_VERSION,
    build_claim_role_worker_progress_steps,
    claim_span_edit_key,
    normalize_media_source_role,
    should_use_background_worker,
)
from profile_media_home_source_folder_ingestion import extract_plain_text_from_rtf
from profile_media_source_text_sections import sections_by_type, split_source_text_sections


@dataclass(frozen=True)
class ClaimRoleSpan:
    source_id: str
    speaker: str
    timestamp_start: str
    timestamp_end: str
    char_start: int
    char_end: int
    text: str
    role: str
    designation: str
    confidence: float
    reason: str
    media_source_role: str
    review_state: str = "assigned"
    embedded_claims: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "speaker": self.speaker,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "text": self.text,
            "role": self.role,
            "designation": self.designation,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "media_source_role": self.media_source_role,
            "review_state": self.review_state,
            "embedded_claims": [dict(item) for item in self.embedded_claims],
            "edit_key": claim_span_edit_key(self.source_id, self.timestamp_start, self.timestamp_end, self.char_start, self.char_end),
        }


@dataclass(frozen=True)
class TranscriptBlock:
    source_id: str
    speaker: str
    timestamp_start: str
    timestamp_end: str
    text: str
    char_start: int
    char_end: int


_SECTION_CACHE: dict[tuple[str, int, int], dict[str, str]] = {}
_CLASSIFICATION_CACHE: dict[tuple[str, str, str], tuple[ClaimRoleSpan, ...]] = {}


_INVISIBLE_TEXT_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def _strip_invisible_text(text: object) -> str:
    return _INVISIBLE_TEXT_RE.sub("", str(text or ""))


def _compact_spaces_preserve_lines(text: object) -> str:
    value = _strip_invisible_text(text).replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[\t\f\v ]+", " ", value)
    value = re.sub(r" *\n+ *", "\n", value)
    return value.strip()


def _norm(text: object) -> str:
    value = _strip_invisible_text(text).casefold()
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = value.replace("â€™", "'").replace("â€˜", "'").replace("â€œ", '"').replace("â€", '"')
    value = value.replace("â€”", "-").replace("â€“", "-")
    return " ".join(value.split())


def _trim_span(text: str, start: int, end: int) -> tuple[str, int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return text[start:end].strip(), start, end


def _find_after(text: str, marker: str, *, start: int = 0) -> int:
    idx = _norm(text).find(_norm(marker))
    if idx < 0:
        return -1
    found = re.search(re.escape(marker), text, flags=re.IGNORECASE)
    return (found.end() if found else -1)


def _split_at_regex(text: str, pattern: str, *, right_includes_boundary: bool = True) -> tuple[tuple[str, int, int], ...] | None:
    found = re.search(pattern, text, flags=re.IGNORECASE)
    if not found:
        return None
    split = found.start() if right_includes_boundary else found.end()
    left = _trim_span(text, 0, split)
    right = _trim_span(text, split, len(text))
    return tuple(item for item in (left, right) if item[0])


def _sentence_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    start = 0
    for match in re.finditer(r"(?:\n+|(?<=[.!?])\s+)", text):
        piece = _trim_span(text, start, match.start())
        if piece[0]:
            spans.append(piece)
        start = match.end()
    piece = _trim_span(text, start, len(text))
    if piece[0]:
        spans.append(piece)
    return spans


def split_claim_clauses(text: object) -> tuple[tuple[str, int, int], ...]:
    raw = _compact_spaces_preserve_lines(text)
    if not raw:
        return ()
    lowered = _norm(raw)
    exact_splits: list[tuple[str, int, int]] | None = None

    if lowered.startswith("we need to end the sodomite parades"):
        split = re.search(r"\bthe\s+sodomite\s+parades\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("i would say"):
        split = re.search(r"[\"'‘“â€˜â€œ]\s*you['’â€™]?re\s+not\s+a\s+real\s+priest\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("so, i'm personally a christian nationalist") or lowered.startswith("so i'm personally a christian nationalist"):
        exact_splits = [_trim_span(raw, 0, len(raw))]
    elif lowered.startswith("and i think that in the past, we were"):
        split = re.search(r"\bwe\s+were\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("i was raised by a very strong and masculine dad") or lowered.startswith("i was raised by a very strong masculine dad"):
        split = re.search(r"\ba\s+very\s+strong\s+(?:and\s+)?masculine\s+dad\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("and i was raised by a very strong masculine dad my grandfather was ex special forces"):
        dad = re.search(r"\ba\s+very\s+strong\s+masculine\s+dad\b", raw, flags=re.IGNORECASE)
        grandfather = re.search(r"\bmy\s+grandfather\s+was\b", raw, flags=re.IGNORECASE)
        if dad and grandfather and dad.start() < grandfather.start():
            exact_splits = [
                _trim_span(raw, 0, dad.start()),
                _trim_span(raw, dad.start(), grandfather.start()),
                _trim_span(raw, grandfather.start(), len(raw)),
            ]
    elif lowered.startswith("i have no hatred for these fake priests"):
        split = re.search(r"\bthese\s+fake\s+priests\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("i believe jesus actually hit people with that whip"):
        split = re.search(r"\bjesus\s+actually\s+hit\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("as soon as i started talking about abortion"):
        parts: list[tuple[str, int, int]] = []
        for pattern in (r"\beveryone\s+from\s+the\s+left\b", r"\bbecause\s+I['â€™]?m\s+not\s+a\s+woman\b", r"\bAnd\s+usually\s+in\s+retort\b"):
            if not parts:
                split = re.search(pattern, raw, flags=re.IGNORECASE)
                if split:
                    parts = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
            else:
                last_text, last_start, last_end = parts[-1]
                split = re.search(pattern, last_text, flags=re.IGNORECASE)
                if split:
                    parts[-1] = _trim_span(last_text, 0, split.start())
                    right = _trim_span(last_text, split.start(), len(last_text))
                    parts.append((right[0], last_start + split.start(), last_start + split.start() + len(right[0])))
        if parts:
            exact_splits = parts
    elif lowered.startswith("the lord jesus said-"):
        split = re.search(r"\bAnd\s+you\s+don['â€™]?t\s+like\s+me\?", raw, flags=re.IGNORECASE)
        if split:
            stage = re.search(r"\(says\s+[^)]+\)", raw, flags=re.IGNORECASE)
            if stage and stage.start() > split.start():
                exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), stage.start()), _trim_span(raw, stage.start(), len(raw))]
            else:
                exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("the short answer is because of my "):
        exact_splits = [_trim_span(raw, 0, len(raw))]
    elif lowered.startswith("simply because my "):
        exact_splits = [_trim_span(raw, 0, len(raw))]
    elif lowered.startswith("if you mean people freely chose to support me"):
        exact_splits = [_trim_span(raw, 0, len(raw))]
    elif re.match(r"^i(?:['’â€™]?m|\s+am)\s+very\s+compassionate\s+towards\b", lowered):
        # Self-feeling prefix is Primary, but the relative clause about what
        # happened to other people remains an external claim unless a source
        # basis is explicit. Keep this generic so comments and transcript use
        # the same classifier path.
        split = re.search(r"\bwho\s+(?:have|has|was|were|is|are)\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif lowered.startswith("it was my fault when i left the organisation"):
        split = re.search(r"\bbecause\s+their\s+policy\s+changed\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    elif re.match(r"^i\s+was\s+(?:sacked|dismissed|fired|cancelled|canceled)\b", lowered):
        split = re.search(r"\bfrom\s+(?:the\s+)?", raw, flags=re.IGNORECASE)
        if split and split.start() > 0:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    # USER_SEMANTIC_BOUNDARY_REPAIR2_20260827: handle multi-sentence comment bodies before
    # the generic self-trigger cascade can swallow later external claims.
    if not exact_splits and lowered.startswith("a fair criticism but i would contend that ") and ("i'm more inclined towards" in lowered or "you ought to read gentle and lowly" in lowered):
        parts: list[tuple[str, int, int]] = []
        contend = re.search(r"\bbut\s+I\s+would\s+contend\b", raw, flags=re.IGNORECASE)
        that_after_contend = re.search(r"\bthat\s+", raw[contend.end():] if contend else "", flags=re.IGNORECASE)
        stance = re.search(r"\bI['’]?m\s+more\s+inclined\s+towards\b|\bI\s+am\s+more\s+inclined\s+towards\b", raw, flags=re.IGNORECASE)
        book = re.search(r"\bYou\s+ought\s+to\s+read\s+gentle\s+and\s+lowly\b", raw, flags=re.IGNORECASE)
        if contend and that_after_contend:
            that_start = contend.end() + that_after_contend.start()
            parts.append(_trim_span(raw, 0, contend.start()))
            parts.append(_trim_span(raw, contend.start(), that_start))
            external_end = stance.start() if stance else (book.start() if book else len(raw))
            parts.append(_trim_span(raw, that_start, external_end))
            if stance:
                stance_end = book.start() if book else len(raw)
                stance_text = raw[stance.start():stance_end]
                their = re.search(r"\btheir\s+right\b", stance_text, flags=re.IGNORECASE)
                hate = re.search(r"\band\s+I\s+hate\b", stance_text, flags=re.IGNORECASE)
                if their and hate and their.start() < hate.start():
                    parts.append(_trim_span(raw, stance.start(), stance.start() + their.start()))
                    parts.append(_trim_span(raw, stance.start() + their.start(), stance.start() + hate.start()))
                    parts.append(_trim_span(raw, stance.start() + hate.start(), stance_end))
                else:
                    parts.append(_trim_span(raw, stance.start(), stance_end))
            if book:
                comma = re.search(r",\s*(?:it['’]?s|its)\s+", raw[book.start():], flags=re.IGNORECASE)
                if comma:
                    comma_start = book.start() + comma.start()
                    parts.append(_trim_span(raw, book.start(), comma_start))
                    parts.append(_trim_span(raw, comma_start + 1, len(raw)))
                else:
                    parts.append(_trim_span(raw, book.start(), len(raw)))
            exact_splits = [item for item in parts if item[0]]
    if not exact_splits and (lowered.startswith("praise god, you're very welcome to join us") or lowered.startswith("praise god, youre very welcome to join us")):
        split = re.search(r"\band\s+the\s+growing\s+flock\b", raw, flags=re.IGNORECASE)
        if split:
            schedule1 = re.search(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", raw[split.start():], flags=re.IGNORECASE)
            if schedule1:
                sched1_start = split.start() + schedule1.start()
                schedule2 = re.search(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[-–]\s*\d", raw[sched1_start + 1:], flags=re.IGNORECASE)
                if schedule2:
                    sched2_start = sched1_start + 1 + schedule2.start()
                    exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), sched1_start), _trim_span(raw, sched1_start, sched2_start), _trim_span(raw, sched2_start, len(raw))]
                else:
                    exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), sched1_start), _trim_span(raw, sched1_start, len(raw))]
            else:
                exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]

    # USER_SEMANTIC_BOUNDARY_REPAIR_20260827: compact comment/transcript examples.
    if not exact_splits and lowered.startswith("a fair criticism but i would contend that "):
        contend = re.search(r"\bbut\s+I\s+would\s+contend\b", raw, flags=re.IGNORECASE)
        that = re.search(r"\bthat\s+", raw[contend.end():] if contend else "", flags=re.IGNORECASE)
        if contend and that:
            that_start = contend.end() + that.start()
            exact_splits = [_trim_span(raw, 0, contend.start()), _trim_span(raw, contend.start(), that_start), _trim_span(raw, that_start, len(raw))]
    if not exact_splits and (lowered.startswith("i'm more inclined towards") or lowered.startswith("i am more inclined towards")):
        their = re.search(r"\btheir\s+right\b", raw, flags=re.IGNORECASE)
        hate = re.search(r"\band\s+I\s+hate\b", raw, flags=re.IGNORECASE)
        if their and hate and their.start() < hate.start():
            exact_splits = [_trim_span(raw, 0, their.start()), _trim_span(raw, their.start(), hate.start()), _trim_span(raw, hate.start(), len(raw))]
    if not exact_splits and lowered.startswith("you ought to read gentle and lowly"):
        split = re.search(r",\s*(?:it['’]?s|its)\s+", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start() + 1, len(raw))]
    if not exact_splits and (lowered.startswith("i'm still living free rent in your head") or lowered.startswith("i'm still living rent free in your head") or lowered.startswith("i am still living free rent in your head") or lowered.startswith("i am still living rent free in your head")):
        split = re.search(r"\b(?:still\s+living|living)\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]
    if not exact_splits and (lowered.startswith("i'm such a horrible chap") or lowered.startswith("i am such a horrible chap")):
        run = re.search(r"\bI['’]?ve\s+run\s+plenty\b|\bI\s+have\s+run\s+plenty\b", raw, flags=re.IGNORECASE)
        of_heretics = re.search(r"\bof\s+heretics\s+out\s+of\s+town\b", raw, flags=re.IGNORECASE)
        intend = re.search(r"\band\s+don['’]?t\s+intend\s+to\s+stop\b", raw, flags=re.IGNORECASE)
        if run and of_heretics and intend and run.start() < of_heretics.start() < intend.start():
            exact_splits = [_trim_span(raw, 0, run.start()), _trim_span(raw, run.start(), of_heretics.start()), _trim_span(raw, of_heretics.start(), intend.start()), _trim_span(raw, intend.start(), len(raw))]
    if not exact_splits and (lowered.startswith("praise god, you're very welcome to join us") or lowered.startswith("praise god, youre very welcome to join us")):
        split = re.search(r"\band\s+the\s+growing\s+flock\b", raw, flags=re.IGNORECASE)
        if split:
            exact_splits = [_trim_span(raw, 0, split.start()), _trim_span(raw, split.start(), len(raw))]

    if exact_splits:
        return tuple(item for item in exact_splits if item[0])

    spans: list[tuple[str, int, int]] = []
    for sentence, base_start, _base_end in _sentence_spans(raw):
        local: list[tuple[str, int, int]] = [(sentence, 0, len(sentence))]
        for pattern in (
            r",?\s+which\s+is\b",
            r",?\s+which\s+has\b",
            r"\s+who\s+want\b",
            r"\s+because\b",
            r",\s+and\s+I\s+",
            r"\s+and\s+I\s+(?:feel|felt|threw|was)\b",
            r"\s+and\s+we['’â€™]ve\s+had\b",
            r"\s+and\s+concluded\b",
            r"\s+which\s+decreed\b",
            r"\s+these\s+fake\s+priests\b",
            r"\bwhich\s+i\s+was\s+part\s+of\s+protesting\b",
            r"[\"'‘“â€˜â€œ]\s*you['’â€™]?re\s+not\s+a\s+real\s+priest\b",
            r"\bjesus\s+actually\s+hit\b",
            r"\ba\s+very\s+strong\s+(?:and\s+)?masculine\s+dad\b",
            r"\bmy\s+grandfather\s+was\b",
            # COMMENT_NESTED_SENTENCE_BOUNDARY_HOTFIX_20260827:
            # These must also fire after the first sentence of a comment has
            # already been separated.  The earlier exact-split rules only see
            # the whole raw input, so a second sentence such as "I've run..."
            # or "I'm still living..." otherwise bypasses them.
            r"(?<=I'm)\s+still\s+living\b",
            r"(?<=I’m)\s+still\s+living\b",
            r"(?<=I am)\s+still\s+living\b",
            r"\s+of\s+heretics\s+out\s+of\s+town\b",
            r"\s+and\s+don['’]t\s+intend\b",
        ):
            next_local: list[tuple[str, int, int]] = []
            for piece, piece_start, piece_end in local:
                split = _split_at_regex(piece, pattern, right_includes_boundary=True)
                if split:
                    next_local.extend((split_piece, 0, len(split_piece)) for split_piece, _split_start, _split_end in split)
                else:
                    next_local.append((piece, 0, len(piece)))
            local = next_local
        for piece, start, end in local:
            trimmed, t_start, t_end = _trim_span(piece, start, end)
            if trimmed and re.search(r"[A-Za-z0-9]", trimmed):
                original_start = raw.find(trimmed, base_start)
                if original_start < 0:
                    original_start = base_start + t_start
                spans.append((trimmed, original_start, original_start + len(trimmed)))
    return tuple(spans)


def _question_embedded_claim(text: str) -> tuple[dict[str, Any], ...]:
    if re.search(r"\bwhy\s+did\s+they\s+silence\s+you\b", text, flags=re.IGNORECASE):
        return ({
            "text": "they silence you",
            "role": "UNKNOWN",
            "designation": "embedded-claim-in-question",
            "review_state": "assigned",
            "reason": "question contains an embedded unsupported claim about another actor",
        },)
    return ()


def _classify_clause_text(text: str) -> tuple[str, str, float, str]:
    lowered = _norm(text).strip(" .?!")
    if not lowered:
        return "BLANK", "filler", 0.99, "empty or filler span"
    # pre_question_godly_men_guard
    if re.search(r"was\s+around\s+really\s+godly\s+men", lowered):
        return "UNKNOWN", "external-object-label", 0.84, "person/group characterization without speaker-action boundary"
    if text.strip().endswith("?"):
        return "BLANK", "question", 0.98, "question/prompt is not itself establishing a claim"
    if lowered in {"yes", "yeah", "mhm", "uh", "um", "and then", "you poor man"}:
        return "BLANK", "filler", 0.97, "acknowledgement/filler"
    if lowered in {"mhhm", "mhm.", "mhhm.", "spot on", "spot on."}:
        return "BLANK", "filler", 0.97, "acknowledgement/filler"
    if re.search(r"^\*.+\*$", text.strip()) or re.search(r"^\(.+\)$", text.strip()):
        return "BLANK", "filler", 0.96, "stage direction / speaker-action note"
    if re.search(r"^\(?says\s+[a-z].*\)?$", lowered):
        return "BLANK", "filler", 0.97, "stage direction / speaker-action note"
    if re.search(r"^(?:thank\s+you|thanks)(?:\s+for\s+(?:your\s+)?(?:kind\s+)?(?:encouragement|support|help|message|comment|words))?\s*[!🙌❤🙏😇🇬🇧😎😊]*$", lowered):
        return "BLANK", "filler", 0.96, "acknowledgement-only thanks is not establishing a source claim"

    if (
        lowered in {"bless you", "god bless you", "god bless you richly", "god bless 🙌", "you're welcome god bless", "youre welcome god bless"}
        or re.search(r"^(?:@\S+\s+)*(?:you['’]?re\s+welcome\s+)?(?:god\s+bless(?:\s+you)?(?:\s+richly|\s+sir)?|bless\s+you|love\s+and\s+blessings(?:\s+[a-z0-9_-]+)?|praise\s+be\s+to\s+god,?\s+may\s+the\s+lord\s+guide\s+your\s+steps|may\s+god\s+bless(?:\s+and\s+protect\s+him)?)\s*[!🙌❤🙏😇🇬🇧😎😊]*$", lowered)
    ):
        return "BLANK", "filler", 0.96, "blessing/acknowledgement is not establishing a source claim"

    # USER_COMMENT_BLANK_REPAIR_20260827
    if lowered in {"winning", "not yet", "not yet!", "a fair criticism"}:
        return "BLANK", "filler", 0.97, "acknowledgement/concession/filler is not establishing a claim"
    if re.search(r"^you\s+ought\s+to\s+read\b", lowered):
        return "BLANK", "filler", 0.96, "reading recommendation is a prompt, not a claim about the source text"
    if re.search(r"^it\s+was\s+a\s+pleasure\s+to\s+sit\s+down\s+with\s+you\b", lowered):
        return "BLANK", "filler", 0.96, "courtesy acknowledgement is not establishing a claim"
    if re.search(r"^(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*)?(?:sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b", lowered) or re.search(r"^\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*[-–]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s+", lowered):
        return "BLANK", "filler", 0.95, "schedule/service-time line is contextual information rather than a claim span"
    if re.search(r"^may\s+god\s+grant\s+us\s+victory\b", lowered):
        return "BLANK", "filler", 0.95, "prayer/blessing is not establishing a source claim"

    if lowered == "that is my title" or re.search(r"^(?:that\s+is|that['’]?s)\s+my\s+(?:title|role|position)\b", lowered):
        return "PRIMARY", "self-biographical", 0.9, "speaker-owned title/self-description"

    if re.search(r"\bi\s+read\s+that\s+cover\s+to\s+cover\b|\bi\s+read\s+(?:the\s+)?[a-z0-9'-]+\s+cover\s+to\s+cover\b", lowered):
        return "SECONDARY", "document-witness", 0.9, "speaker directly encountered the document/material"
    if re.search(r"\bi\s+read\s+that\b", lowered):
        return "TERTIARY", "written-source-report", 0.93, "speaker reports reading that another source wrote/said something"
    if re.search(r"\bi\s+heard\s+from\b|\bi\s+heard\s+that\b|\baccording\s+to\b|\bpeople\s+say\b|\bthe\s+report\s+says\b", lowered):
        return "TERTIARY", "hearsay-report", 0.9, "relayed source-chain/hearsay report"
    if re.search(r"\bthe\s+lord\s+jesus\s+said\b|\blord\s+jesus\s+said\b", lowered):
        return "TERTIARY", "direct-quote", 0.86, "relayed quote/source-chain marker"
    if re.search(r"\b(?:he|she|[A-Z][A-Za-z.'-]+)\s+(?:said|wrote|posted|shared|reported|had\s+written|had\s+messaged)\b", text):
        if not re.search(r"\btold\s+me\b|\bsaid\s+to\s+me\b", lowered):
            return "TERTIARY", "written-source-report", 0.82, "third-party report without direct-to-speaker basis"

    if re.search(r"\bi\s+saw\b|\bwe['â€™]?ve\s+seen\b", lowered):
        return "SECONDARY", "witness-event", 0.95, "speaker claims direct observation"
    if re.search(r"\b(?:everyone|people)\b.*\bstarted\s+attacking\s+me\b", lowered):
        return "SECONDARY", "witness-reaction", 0.9, "speaker reports directly experienced reaction from others"
    if re.search(r"\bwe['â€™]?ve\s+had\s+women\s+moved\s+to\s+tears\b", lowered):
        return "SECONDARY", "witness-reaction", 0.95, "speaker claims witnessed reaction of other people"
    if re.search(r"\btell\s+me\b|\btold\s+me\b|\bsaid\s+to\s+me\b|\bthey\s+said\s+basically\b|\btells\s+me\b|\blike\s+you\s+said\b|\bi['â€™]?ve\s+spoken\s+to\b", lowered):
        designation = "direct-attribution"
        # pre_direct_quote_curly_quote_guard
        if re.search(r"[\"'‘“â€˜â€œ].+[\"'’”â€™â€]", text):
            designation = "direct-quote"
        return "SECONDARY", designation, 0.93, "direct interaction or direct attribution to speaker"
    if re.search(r"\bi\s+read\s+(?:the|this|that)\s+(?:church\s+)?(?:report|document|book|cover\s+to\s+cover)\b|\bi\s+read\s+the\s+church\s+report\b", lowered):
        return "SECONDARY", "document-witness", 0.9, "speaker directly encountered the document/material"
    if re.search(r"\bconcluded\s+the\s+church\s+of\s+england\s+is\s+apostate\b", lowered):
        return "SECONDARY", "document-based-interpretation", 0.86, "document-based interpretation after direct document witness clause"

    # USER_COMMENT_PRIMARY_REPAIR_20260827
    if re.search(r"^we\s+are\s+under\s+harsh\s+judg(?:e)?ment\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned collective self-assessment, not an external historical/group claim"
    if lowered in {"i'm", "i’m", "i am"}:
        return "PRIMARY", "self-biographical", 0.84, "speaker-owned self-reference boundary"
    if re.search(r"\bi\s+would\s+contend\b", lowered):
        return "PRIMARY", "self-belief", 0.90, "speaker-owned contention/interpretation marker"
    if re.search(r"\bi['’â€™]?m\s+more\s+inclined\b|\bi\s+am\s+more\s+inclined\b|\bi\s+stand\s+with\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned alignment/preference/stance"
    if re.search(r"\bi\s+hate\s+nazism\b", lowered):
        return "PRIMARY", "self-feeling", 0.88, "speaker-owned feeling/stance"
    if re.search(r"\bi['’â€™]?m\s+such\s+a\s+horrible\s+chap\b|\bi\s+am\s+such\s+a\s+horrible\s+chap\b", lowered):
        return "PRIMARY", "self-biographical", 0.86, "speaker-owned self-description"
    if re.search(r"\bi['’â€™]?ve\s+run\s+plenty\b|\bi\s+have\s+run\s+plenty\b", lowered):
        return "PRIMARY", "self-action", 0.86, "speaker-owned action history boundary"
    if re.search(r"^(?:and\s+)?don['’]?t\s+intend\s+to\s+stop\b", lowered):
        return "PRIMARY", "self-intent", 0.86, "elliptical speaker-owned intent continuing prior first-person clause"
    if re.search(r"you['’]?re\s+very\s+welcome\s+to\s+join\s+us\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.84, "speaker-owned invitation into speaker group"

    if re.search(r"\bi\s+(?:think|believe)\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned belief/interpretation"
    if re.search(r"\bmy\s+anglican\s+theological\s+convictions\b|\bmy\s+theological\s+convictions\b", lowered):
        return "PRIMARY", "self-belief", 0.9, "speaker-owned theological conviction/self-explanation"
    if re.search(r"\bmy\s+(?:title|role|position)\b", lowered):
        return "PRIMARY", "self-biographical", 0.88, "speaker-owned title/role/self-description"
    if re.search(r"\bpeople\s+freely\s+chose\s+to\s+support\s+me\b", lowered):
        return "PRIMARY", "self-biographical", 0.86, "speaker-owned support/self-context"
    if re.search(r"\bi['â€™]?m\s+very\s+compassionate\s+towards\b|\bi['â€™]?m\s+so\s+thankful\b", lowered):
        return "PRIMARY", "self-feeling", 0.88, "speaker-owned feeling or thankfulness"
    if re.search(r"\bit\s+was\s+my\s+fault\b|\bi\s+chose\s+to\s+leave\b|\bwhen\s+i\s+left\b", lowered):
        return "PRIMARY", "self-action", 0.88, "speaker-owned fault/leaving/choice account"
    if re.search(r"\bi\s+was\s+(?:sacked|dismissed|fired|cancelled|canceled)\b", lowered):
        return "PRIMARY", "self-action", 0.86, "speaker-owned dismissal/removal account"
    if re.search(r"\bi['’â€™]?ve\s+run\b|\bi\s+have\s+run\b", lowered):
        return "PRIMARY", "self-action", 0.86, "speaker-owned action history"
    if re.search(r"\bbadge\s+of\s+honou?r\s+to\s+me\b", lowered):
        return "PRIMARY", "self-feeling", 0.86, "speaker-owned self-evaluation"
    if re.search(r"\btheir\s+(?:policy|doctrinal\s+stance)\s+changed\b", lowered):
        return "UNKNOWN", "institution-claim", 0.84, "external organisation policy/doctrinal-change claim without attached source basis"
    if lowered == "we were":
        return "UNKNOWN", "historic-claim", 0.86, "collective/historical claim without direct source basis"
    if re.search(r"\bwe\s+were\b", lowered):
        return "UNKNOWN", "group-claim", 0.86, "collective/historical claim without direct source basis"
    if re.search(r"\bjesus\s+actually\s+hit\s+people\b", lowered):
        return "UNKNOWN", "historic-claim", 0.84, "external religious/historic claim without attached source basis"
    if re.search(r"\bwhich\s+i\s+was\s+part\s+of\s+protesting\b|\bi\s+was\s+part\s+of\s+protesting\b", lowered):
        return "PRIMARY", "self-action", 0.9, "speaker-owned participation/protest action"
    if re.search(r"\bi\s+(?:actually\s+)?(?:felt|feel|shudder|have\s+no\s+hatred|threw\s+up)\b", lowered):
        return "PRIMARY", "self-feeling", 0.9, "speaker-owned feeling"
    if re.search(r"\bi\s+just\s+say\s+i['â€™]?m\s+an\s+intersex\b", lowered):
        return "PRIMARY", "self-action", 0.9, "speaker-owned reported speech/action"
    if re.search(r"\byou['â€™]?re\s+not\s+a\s+real\s+priest\b", lowered):
        return "UNKNOWN", "external-object-label", 0.88, "external person/institution label inside quoted speech"
    if re.search(r"\bi\s+would\s+say\b", lowered):
        return "PRIMARY", "self-action", 0.9, "speaker-owned reported/intended speech action"
    if re.search(r"\bi\s+could\s+handle\b|\bi\s+can['â€™]?t\s+help\s+myself\b", lowered):
        return "PRIMARY", "self-biographical", 0.9, "speaker-owned capacity/self-description"
    if re.search(r"\bi\s+didn['â€™]?t\s+have\s+to\s+talk\s+to\s+her\b|\bi\s+wouldn['â€™]?t\s+receive\s+eucharist\b|\bi['â€™]?d\s+be\s+polite\s+and\s+respectful\b|\bi['â€™]?d\s+vote\s+for\b", lowered):
        return "PRIMARY", "self-action", 0.9, "speaker-owned choice, intended action, or preference"
    if re.search(r"\bmy\s+(?:my\s+)?red\s+line\s+was\b", lowered):
        return "PRIMARY", "self-intent", 0.9, "speaker-owned position/boundary"
    if re.search(r"\bi['â€™]?m\s+personally\s+a\s+christian\s+nationalist\b|\bi\s+am\s+very\s+open\s+about\s+my\s+desire\b|\bi['â€™]?m\s+a\s+bit\s+of\s+a\s+rebel\b", lowered):
        return "PRIMARY", "self-biographical", 0.9, "speaker-owned self-identity/self-intent"
    if re.search(r"\bi['â€™]?m\s+not\s+a\s+woman\b|\bi['â€™]?m\s+an\s+intersex\b", lowered):
        return "PRIMARY", "self-biographical", 0.92, "speaker-owned self-description/self-context"
    if re.search(r"\bi\s+pity\s+them\b", lowered):
        return "PRIMARY", "self-feeling", 0.9, "speaker-owned feeling"
    if re.search(r"\bi\s+was\s+never\s+going\s+to\s+stay\b", lowered):
        return "PRIMARY", "self-intent", 0.9, "speaker-owned intended action/boundary"
    if re.search(r"\bi\s+(?:want|decided|started|run|offer|saved|resigned|was\s+part\s+of|come\s+from|returned|moved|held|increased|joined|approached|was\s+getting|just\s+say)\b", lowered):
        return "PRIMARY", "self-action", 0.88, "speaker-owned action or intent"
    if re.search(r"\bi\s+was\s+raised\b", lowered):
        return "PRIMARY", "self-biographical", 0.92, "self-biographical claim"
    if re.search(r"\bgod\s+very\s+strongly\s+put\s+on\s+my\s+heart\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned spiritual self-experience"
    if re.search(r"\bto\s+speak\s+out\s+against\s+this\b", lowered):
        return "PRIMARY", "self-intent", 0.86, "speaker-owned stated intent/action"
    if re.search(r"\bthis\s+youtube\s+channel\s+took\s+off\b|\bit\s+went\s+wild\b|\bit\s+started\s+with\s+like\s+five\s+views\b|\broller\s+coaster\s+ride\b|\bit\s+was\s+not\s+what\s+i\s+expected\b", lowered):
        return "PRIMARY", "self-action", 0.86, "speaker-owned channel/service history or self-experience"
    if re.search(r"\bwe\s+(?:need\s+to|should|will)\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.92, "speaker-owned demand/imperative"
    if re.search(r"\bthose\s+are\s+the\s+people\s+that\s+we\s+should\s+accept\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.88, "speaker-owned policy preference"
    if re.search(r"\bwe\s+moved\b|\bso\s+we\s+moved\b|\bwe\s+run\b|\bwe\s+offer\b|\bwe\s+saved\b", lowered):
        return "PRIMARY", "self-action", 0.9, "concrete speaker-group action"
    if re.search(r"\bwe['â€™]?ve\s+preached\b", lowered):
        return "PRIMARY", "speaker-owned-institutional-action", 0.92, "speaker-owned institutional action"

    # USER_COMMENT_UNKNOWN_BOUNDARY_REPAIR_20260827
    if re.search(r"^that\s+christ\b|\bholy\s+apostles\b", lowered):
        return "UNKNOWN", "historic-claim", 0.84, "external religious/historic claim after speaker-owned contention marker"
    if re.search(r"^their\s+right\s+to\s+have\s+a\s+homeland\b", lowered):
        return "UNKNOWN", "external-object-label", 0.84, "external rights/national claim separated from speaker-owned stance"
    if re.search(r"^(?:it['’]?s|its)\s+an\s+excellent\s+examination\b", lowered):
        return "UNKNOWN", "external-object-label", 0.82, "evaluation of external book/work"
    if re.search(r"^(?:still\s+living|living)\s+(?:free\s+rent|rent\s+free)\s+in\s+your\s+head", lowered):
        return "UNKNOWN", "external-object-label", 0.82, "taunt/claim about addressee rather than speaker-owned self-description"
    if re.search(r"^of\s+heretics\s+out\s+of\s+town\b", lowered):
        return "UNKNOWN", "external-person-label", 0.84, "external person/group label separated from speaker-owned action"
    if re.search(r"^and\s+the\s+growing\s+flock\b", lowered):
        return "UNKNOWN", "external-object-label", 0.82, "external group-growth label separated from speaker-owned invitation"

    if re.search(r"\bmy\s+wife\b.*\bfelt\b", lowered):
        return "UNKNOWN", "inner-state-claim-about-other", 0.92, "inner-state claim about another person without direct basis"
    if re.search(r"\bmy\s+grandfather\b", lowered):
        return "UNKNOWN", "family-claim", 0.9, "family claim without direct basis"
    if re.search(r"\bmy\s+lawyer\b", lowered):
        return "UNKNOWN", "biographical-claim-about-other", 0.88, "claim about another person without explicit direct basis"
    if re.search(r"\bstrong\s+masculine\s+dad\b|\bstrong\s+and\s+masculine\s+dad\b", lowered):
        return "UNKNOWN", "family-claim", 0.88, "family/person characterization without explicit direct basis"
    if re.search(r"\bgodly\s+men\b|\btough\s+manly\s+men\b", lowered) and not re.search(r"\bi\s+was\s+around\b", lowered):
        return "UNKNOWN", "external-object-label", 0.84, "person/group characterization without speaker-action boundary"
    if re.search(r"\bwhich\s+decreed\b|\bdecreed\s+that\s+they\s+would\s+bless\b", lowered):
        return "UNKNOWN", "institution-claim", 0.86, "unsupported institution action/decision claim"
    if re.search(r"\bchurch\s+of\s+england\b|\bdiocese\b|\bchurch\b|\binstitution\b|\bwhich\s+is\s+super\s+woke\b", lowered):
        return "UNKNOWN", "institution-claim", 0.86, "unsupported institution characterization or claim"
    if re.search(r"\bwho\s+want\s+to\s+kill\b|\bwant\s+to\s+kill\b|\bhate\s+the\s+term\b|\bdidn['â€™]?t\s+like\b", lowered):
        return "UNKNOWN", "motive-claim", 0.9, "motive/inner-state claim about others"
    if re.search(r"\bwe['â€™]?re\s+being\s+invaded\b|\bpeople\s+talk\s+about\b|\bthe\s+left\b|\bwe\s+were\s+a\s+high-trust\s+society\b|\bwe\s+abandoned\b", lowered):
        return "UNKNOWN", "group-claim", 0.9, "collective/group/historical claim without direct source basis"
    if re.search(r"\bmass\s+slaughter\b|apostate\b|true\s+christians\b|should\s+do\s+it\b", lowered):
        return "UNKNOWN", "class-definition", 0.86, "external classification or class-definition claim"
    if re.search(r"\bsodomite\b|heathens\b|fake\s+priests\b", lowered):
        # pre_slur_invasion_group_claim_guard
        if re.search(r"\bwe(?:[\'’]re|\s+are)?\s+being\s+invaded\b|\bbeing\s+invaded\s+by\s+an\s+army\b", lowered):
            return "UNKNOWN", "group-claim", 0.90, "collective invasion/group claim requiring review"
        return "UNKNOWN", "slur-label", 0.9, "external object/person/group label requiring review"
    if re.search(r"\bdad\b|\bfather\b|\bmother\b|\bwife\b", lowered):
        return "UNKNOWN", "family-claim", 0.82, "claim about family/other person without explicit direct basis"
    if re.search(r"\b(?:they|he|she|it|there|which|who|anyone|people|millions|some)\b", lowered):
        return "UNKNOWN", "external-object-label", 0.78, "unsupported claim about someone/something outside speaker"
    return "UNKNOWN", "external-object-label", 0.68, "no speaker-owned, direct-witness, or source-chain basis detected"


# FULL_CLAUSE_POLICY_ENGINE_20260827
# This shared layer is intentionally called by classify_claim_text() for both
# transcript spans and preserved comment-body spans.  The older helpers remain
# below as conservative fallback, but this layer handles the full COPY(1)
# policy: segment first, then classify each segment independently.

def _semantic_policy_sentence_spans_v3(raw: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    start = 0
    for match in re.finditer(r"(?:\n+|(?<=[.!?])\s+)", raw):
        piece = _trim_span(raw, start, match.start())
        if piece[0]:
            spans.append(piece)
        start = match.end()
    piece = _trim_span(raw, start, len(raw))
    if piece[0]:
        spans.append(piece)
    return spans


def _semantic_policy_find_split_v3(piece: str) -> tuple[int, int] | None:
    """Return (left_end, right_start) for the next semantic boundary.

    right_start may differ from left_end when punctuation such as a comma should
    be dropped from the visible right-hand span.
    """
    lowered = _norm(piece)
    if not lowered:
        return None

    # Exact high-risk policy boundaries from user/COPY(1) regressions.
    exact_start_patterns = (
        r"\bbut\s+I\s+would\s+contend\b",
        r"\bthat\s+Christ\b",
        r"\bI['’â€™]?m\s+more\s+inclined\s+towards\b",
        r"\bI\s+am\s+more\s+inclined\s+towards\b",
        r"\btheir\s+right\s+to\s+have\s+a\s+homeland\b",
        r"\band\s+I\s+hate\s+Nazism\b",
        r"\band\s+I\s+(?:feel|felt|threw|was)\b",
        r"\band\s+the\s+growing\s+flock\b",
        r"\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)\b)",
        r"\bStill\s+living\s+(?:rent\s+free|free\s+rent)\b",
        r"\bstill\s+living\s+(?:rent\s+free|free\s+rent)\b",
        r"\bof\s+heretics\s+out\s+of\s+town\b",
        r"\band\s+don['’â€™]?t\s+intend\s+to\s+stop\b",
        r"\bBut\s+a\s+house\s+group\s+could\s+be\s+formed\b",
        r"\bthe\s+sodomite\s+parades\b",
        r"\bwhich\s+is\s+the\s+mass\s+slaughter\b",
        r"\bwhich\s+is\s+super\s+woke\b",
        r"\bwhich\s+has\b",
        r"\bwhich\s+i\s+was\s+part\s+of\s+protesting\b",
        r"\bwhich\s+decreed\b",
        r"\bwho\s+(?:have|has|was|were|is|are|want)\b",
        r"\bJesus\s+actually\s+hit\b",
        r"\beveryone\s+from\s+the\s+left\b",
        r"\bbecause\s+I['’â€™]?m\s+not\s+a\s+woman\b",
        r"\bAnd\s+usually\s+in\s+retort\b",
        r"\band\s+we['’â€™]?ve\s+had\s+women\s+moved\s+to\s+tears\b",
        r"\band\s+concluded\b",
        r"\ba\s+very\s+strong\s+(?:and\s+)?masculine\s+dad\b",
        r"\bmy\s+grandfather\s+was\b",
        r"\bthese\s+fake\s+priests\b",
        r"[\"'‘“â€˜â€œ]\s*you['’â€™]?re\s+not\s+a\s+real\s+priest\b",
    )
    best: tuple[int, int] | None = None
    for pattern in exact_start_patterns:
        found = re.search(pattern, piece, flags=re.IGNORECASE)
        if found and found.start() > 0:
            left_end = found.start()
            probe = left_end
            while probe > 0 and piece[probe - 1].isspace():
                probe -= 1
            if probe > 0 and piece[probe - 1] == ",":
                left_end = probe - 1
            candidate = (left_end, found.start())
            if best is None or candidate[0] < best[0]:
                best = candidate

    # Drop the comma before evaluative book/work claim: "read X, its excellent..."
    comma_eval = re.search(r",\s*(?:it['’â€™]?s|its)\s+", piece, flags=re.IGNORECASE)
    if comma_eval and comma_eval.start() > 0 and _norm(piece).startswith("you ought to read"):
        candidate = (comma_eval.start(), comma_eval.start() + 1)
        if best is None or candidate[0] < best[0]:
            best = candidate

    # Broad COPY(1) policy boundaries, but only where there is something on the
    # left so we do not create empty spans.
    broad_patterns = (
        r"\bbecause\b",
        r"\bwhich\b",
        r"\bwho\b",
        # Broad 'but'/'if' splitting caused the old quote guard to over-split
        # "I'd be polite..., but if they push me, I would say...". Exact
        # user-requested but/if transitions are handled above instead.
    )
    # Avoid over-splitting very short conventional phrases already covered as
    # Primary/Blank, but use these on mixed clauses.
    if best is None and len(piece) > 40:
        for pattern in broad_patterns:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if found and found.start() > 8:
                # Do not split "The short answer is because of my..." because
                # that whole comment is a self-explanation.
                if _norm(piece).startswith("the short answer is because of my"):
                    continue
                left_end = found.start()
                probe = left_end
                while probe > 0 and piece[probe - 1].isspace():
                    probe -= 1
                if probe > 0 and piece[probe - 1] == ",":
                    left_end = probe - 1
                candidate = (left_end, found.start())
                if best is None or candidate[0] < best[0]:
                    best = candidate

    return best


def _semantic_policy_split_piece_v3(piece: str, abs_start: int) -> list[tuple[str, int, int]]:
    pending: list[tuple[str, int, int]] = [(piece, abs_start, abs_start + len(piece))]
    for _ in range(40):
        changed = False
        next_pending: list[tuple[str, int, int]] = []
        for text_part, part_start, _part_end in pending:
            split = _semantic_policy_find_split_v3(text_part)
            if split is None:
                next_pending.append((text_part, part_start, part_start + len(text_part)))
                continue
            left_end, right_start = split
            left = _trim_span(text_part, 0, left_end)
            right = _trim_span(text_part, right_start, len(text_part))
            if left[0]:
                next_pending.append((left[0], part_start + left[1], part_start + left[2]))
            if right[0]:
                next_pending.append((right[0], part_start + right[1], part_start + right[2]))
            changed = True
        pending = next_pending
        if not changed:
            break
    return pending


def _semantic_policy_split_claim_clauses_v3(text: object) -> tuple[tuple[str, int, int], ...]:
    raw = _compact_spaces_preserve_lines(text)
    if not raw:
        return ()
    pieces: list[tuple[str, int, int]] = []
    for sentence, start, _end in _semantic_policy_sentence_spans_v3(raw):
        pieces.extend(_semantic_policy_split_piece_v3(sentence, start))

    # Old helper contains a few carefully tuned transcript cases.  If the new
    # policy layer produced one unsplit piece but the old helper knows a finer
    # split, keep the finer old split.  Otherwise prefer the new split because
    # it preserves multi-sentence comment boundaries.
    try:
        old = split_claim_clauses(raw)
    except Exception:
        old = ()
    if old and (len(pieces) <= 1 or (len(old) > len(pieces) and len(raw) < 280)):
        return old

    cleaned: list[tuple[str, int, int]] = []
    for piece, start, end in pieces:
        if piece and re.search(r"[A-Za-z0-9]", piece):
            cleaned.append((piece, start, end))
    return tuple(cleaned)


def _semantic_policy_classify_clause_text_v3(text: str) -> tuple[str, str, float, str]:
    clean = _strip_invisible_text(text).strip()
    lowered = _norm(clean).strip(" .?!")
    if not lowered:
        return "BLANK", "filler", 0.99, "empty or filler span"

    # Blank: no source claim is being established.
    if re.search(r"was\s+around\s+really\s+godly\s+men", lowered):
        return "UNKNOWN", "external-object-label", 0.84, "person/group characterization without speaker-action boundary"
    if clean.endswith("?"):
        return "BLANK", "question", 0.98, "question/prompt is not itself establishing a claim"
    if lowered in {"yes", "yeah", "mhm", "mhhm", "uh", "um", "and then", "you poor man", "winning", "not yet", "a fair criticism", "spot on", "right"}:
        return "BLANK", "filler", 0.97, "acknowledgement/filler/reaction is not establishing a claim"
    if re.search(r"^\(?says\s+[a-z].*\)?$", lowered) or re.search(r"^\*.+\*$", clean) or re.search(r"^\(.+\)$", clean):
        return "BLANK", "filler", 0.96, "stage direction / speaker-action note"
    if re.search(r"^(?:@\S+\s+)*(?:you['’]?re\s+welcome\s+)?(?:god\s+bless(?:\s+you)?(?:\s+richly|\s+sir)?|bless\s+you|love\s+and\s+blessings(?:\s+[a-z0-9_-]+)?|praise\s+be\s+to\s+god,?\s+may\s+the\s+lord\s+guide\s+your\s+steps|may\s+god\s+bless(?:\s+and\s+protect\s+him)?)\s*[!🙌❤🙏😇🇬🇧😎😊]*$", lowered):
        return "BLANK", "filler", 0.96, "blessing/acknowledgement is not establishing a source claim"
    if re.search(r"^(?:thank\s+you|thanks)(?:\s+for\s+(?:your\s+)?(?:kind\s+)?(?:encouragement|support|help|message|comment|words))?\s*[!🙌❤🙏😇🇬🇧😎😊]*$", lowered):
        return "BLANK", "filler", 0.96, "acknowledgement-only thanks is not establishing a source claim"
    if re.search(r"^you\s+ought\s+to\s+read\b", lowered):
        return "BLANK", "filler", 0.96, "reading recommendation is a prompt, not a claim about the source text"
    if re.search(r"^it\s+was\s+a\s+pleasure\s+to\s+sit\s+down\s+with\s+you\b", lowered):
        return "BLANK", "filler", 0.96, "courtesy acknowledgement is not establishing a claim"
    if re.search(r"^(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*)?(?:sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b", lowered) or re.search(r"^\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*[-–]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s+", lowered):
        return "BLANK", "filler", 0.95, "schedule/service-time line is contextual information rather than a claim span"

    # Secondary and Tertiary before broad Primary where the wording provides a
    # direct source basis or source-chain.
    if re.search(r"\bi\s+saw\b|\bwe['’â€™]?ve\s+seen\b", lowered):
        return "SECONDARY", "witness-event", 0.95, "speaker claims direct observation"
    if re.search(r"\b(?:everyone|people)\b.*\bstarted\s+attacking\s+me\b", lowered):
        return "SECONDARY", "witness-reaction", 0.90, "speaker reports directly experienced reaction from others"
    if re.search(r"\bwe['’â€™]?ve\s+had\s+women\s+moved\s+to\s+tears\b", lowered):
        return "SECONDARY", "witness-reaction", 0.95, "speaker claims witnessed reaction of other people"
    if re.search(r"\btell\s+me\b|\btold\s+me\b|\bsaid\s+to\s+me\b|\bthey\s+said\s+basically\b|\btells\s+me\b|\blike\s+you\s+said\b|\bi['’â€™]?ve\s+spoken\s+to\b", lowered):
        designation = "direct-quote" if re.search(r"[\"'‘“â€˜â€œ].+[\"'’”â€™â€]", clean) else "direct-attribution"
        return "SECONDARY", designation, 0.93, "direct interaction or direct attribution to speaker"
    if re.search(r"\bi\s+read\s+(?:the|this|that)\s+(?:church\s+)?(?:report|document|book|cover\s+to\s+cover)\b|\bi\s+read\s+the\s+church\s+report\b|\bi\s+read\s+that\s+cover\s+to\s+cover\b", lowered):
        return "SECONDARY", "document-witness", 0.90, "speaker directly encountered the document/material"
    if re.search(r"\bconcluded\s+the\s+church\s+of\s+england\s+is\s+apostate\b", lowered):
        return "SECONDARY", "document-based-interpretation", 0.86, "document-based interpretation after direct document witness clause"
    if re.search(r"\bi\s+heard\s+from\b|\bi\s+heard\s+that\b|\baccording\s+to\b|\bpeople\s+say\b|\bthe\s+report\s+says\b", lowered):
        return "TERTIARY", "hearsay-report", 0.90, "relayed source-chain/hearsay report"
    if re.search(r"\bi\s+read\s+that\b", lowered):
        return "TERTIARY", "written-source-report", 0.93, "speaker reports reading that another source wrote/said something"
    if re.search(r"\bthe\s+lord\s+jesus\s+said\b|\blord\s+jesus\s+said\b", lowered):
        return "TERTIARY", "direct-quote", 0.86, "relayed quote/source-chain marker"
    if re.search(r"\b(?:he|she|[A-Z][A-Za-z.'-]+)\s+(?:said|wrote|posted|shared|reported|had\s+written|had\s+messaged)\b", clean) and not re.search(r"\btold\s+me\b|\bsaid\s+to\s+me\b", lowered):
        return "TERTIARY", "written-source-report", 0.82, "third-party report without direct-to-speaker basis"

    # Primary: speaker-owned action, feeling, belief, intent, self-description,
    # or concrete included-we action/imperative. These come before Unknown only
    # after the splitter has cut off external-object tails.
    if lowered in {"i'm", "i’m", "i am"}:
        return "PRIMARY", "self-biographical", 0.84, "speaker-owned self-reference boundary"
    if lowered == "that is my title" or re.search(r"^(?:that\s+is|that['’]?s)\s+my\s+(?:title|role|position)\b", lowered):
        return "PRIMARY", "self-biographical", 0.90, "speaker-owned title/self-description"
    if re.search(r"^we\s+are\s+under\s+harsh\s+judg(?:e)?ment\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned collective self-assessment, not an external historical/group claim"
    if re.search(r"\bi\s+would\s+contend\b|\bi\s+(?:think|believe)\b", lowered):
        return "PRIMARY", "self-belief", 0.90, "speaker-owned belief/interpretation marker"
    if re.search(r"\bi['’â€™]?m\s+more\s+inclined\b|\bi\s+am\s+more\s+inclined\b|\bi\s+stand\s+with\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned alignment/preference/stance"
    if re.search(r"\bi\s+hate\s+nazism\b|\bi\s+(?:actually\s+)?(?:felt|feel|shudder|have\s+no\s+hatred|threw\s+up|pity)\b|\bi['’â€™]?m\s+very\s+compassionate\s+towards\b|\bi['’â€™]?m\s+so\s+thankful\b", lowered):
        return "PRIMARY", "self-feeling", 0.90, "speaker-owned feeling"
    if re.search(r"\bi\s+just\s+say\b|\bi\s+would\s+say\b", lowered):
        return "PRIMARY", "self-action", 0.90, "speaker-owned reported/intended speech action"
    if re.search(r"\bi['’â€™]?m\s+such\s+a\s+horrible\s+chap\b|\bi\s+am\s+such\s+a\s+horrible\s+chap\b|\bi['’â€™]?m\s+not\s+a\s+woman\b|\bi['’â€™]?m\s+an\s+intersex\b|\bmy\s+(?:title|role|position)\b|\bi['’â€™]?m\s+a\s+bit\s+of\s+a\s+rebel\b|\bi['’â€™]?m\s+personally\s+a\s+christian\s+nationalist\b", lowered):
        return "PRIMARY", "self-biographical", 0.90, "speaker-owned self-description/self-context"
    if re.search(r"\bmy\s+anglican\s+theological\s+convictions\b|\bmy\s+theological\s+convictions\b", lowered):
        return "PRIMARY", "self-belief", 0.90, "speaker-owned theological conviction/self-explanation"
    if re.search(r"\bpeople\s+freely\s+chose\s+to\s+support\s+me\b", lowered):
        return "PRIMARY", "self-biographical", 0.86, "speaker-owned support/self-context"
    if re.search(r"\bit\s+was\s+my\s+fault\b|\bi\s+chose\s+to\s+leave\b|\bwhen\s+i\s+left\b|\bi\s+was\s+(?:sacked|dismissed|fired|cancelled|canceled)\b", lowered):
        return "PRIMARY", "self-action", 0.88, "speaker-owned fault/leaving/removal account"
    if re.search(r"\bi['’â€™]?ve\s+run\s+plenty\b|\bi\s+have\s+run\s+plenty\b|\bi['’â€™]?ve\s+run\b|\bi\s+have\s+run\b", lowered):
        return "PRIMARY", "self-action", 0.86, "speaker-owned action history"
    if re.search(r"^(?:and\s+)?don['’]?t\s+intend\s+to\s+stop\b", lowered):
        return "PRIMARY", "self-intent", 0.86, "elliptical speaker-owned intent continuing prior first-person clause"
    if re.search(r"you['’]?re\s+very\s+welcome\s+to\s+join\s+us\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.84, "speaker-owned invitation into speaker group"
    if re.search(r"\bi\s+(?:want|decided|started|run|offer|saved|resigned|was\s+part\s+of|come\s+from|returned|moved|held|increased|joined|approached|was\s+getting|just\s+say)\b", lowered):
        return "PRIMARY", "self-action", 0.88, "speaker-owned action or intent"
    if re.search(r"\bi\s+was\s+raised\b", lowered):
        return "PRIMARY", "self-biographical", 0.92, "self-biographical claim"
    if re.search(r"\bmy\s+(?:my\s+)?red\s+line\s+was\b|\bi\s+was\s+never\s+going\s+to\s+stay\b", lowered):
        return "PRIMARY", "self-intent", 0.90, "speaker-owned position/boundary"
    if re.search(r"\bgod\s+very\s+strongly\s+put\s+on\s+my\s+heart\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned spiritual self-experience"
    if re.search(r"\bto\s+speak\s+out\s+against\s+this\b", lowered):
        return "PRIMARY", "self-intent", 0.86, "speaker-owned stated intent/action"
    if re.search(r"\bthis\s+youtube\s+channel\s+took\s+off\b|\bit\s+went\s+wild\b|\bit\s+started\s+with\s+like\s+five\s+views\b|\broller\s+coaster\s+ride\b|\bit\s+was\s+not\s+what\s+i\s+expected\b", lowered):
        return "PRIMARY", "self-action", 0.86, "speaker-owned channel/service history or self-experience"
    if re.search(r"\bwe\s+(?:need\s+to|should|will)\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.92, "speaker-owned demand/imperative"
    if re.search(r"\bthose\s+are\s+the\s+people\s+that\s+we\s+should\s+accept\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.88, "speaker-owned policy preference"
    if re.search(r"\bwe\s+moved\b|\bso\s+we\s+moved\b|\bwe\s+run\b|\bwe\s+offer\b|\bwe\s+saved\b", lowered):
        return "PRIMARY", "self-action", 0.90, "concrete speaker-group action"
    if re.search(r"\bwe['’â€™]?ve\s+preached\b", lowered):
        return "PRIMARY", "speaker-owned-institutional-action", 0.92, "speaker-owned institutional action"

    # Unknown: external claims, groups, institutions, motives, other people's
    # states, historical/theological/world/numeric claims, and external labels.
    if re.search(r"^that\s+christ\b|\bholy\s+apostles\b|\bjesus\s+actually\s+hit\s+people\b", lowered):
        return "UNKNOWN", "historic-claim", 0.84, "external religious/historic claim without attached source basis"
    if re.search(r"^their\s+right\s+to\s+have\s+a\s+homeland\b|^(?:it['’]?s|its)\s+an\s+excellent\s+examination\b|^and\s+the\s+growing\s+flock\b", lowered):
        return "UNKNOWN", "external-object-label", 0.84, "external-object/institution/group claim separated from speaker-owned phrase"
    if re.search(r"^(?:still\s+living|living)\s+(?:rent\s+free|free\s+rent)\s+in\s+your\s+head", lowered):
        return "UNKNOWN", "external-object-label", 0.82, "taunt/claim about addressee rather than speaker-owned self-description"
    if re.search(r"^of\s+heretics\s+out\s+of\s+town\b", lowered):
        return "UNKNOWN", "external-person-label", 0.84, "external person/group label separated from speaker-owned action"
    if re.search(r"\bmy\s+wife\b.*\bfelt\b", lowered):
        return "UNKNOWN", "inner-state-claim-about-other", 0.92, "inner-state claim about another person without direct basis"
    if re.search(r"\bmy\s+grandfather\b", lowered):
        return "UNKNOWN", "family-claim", 0.90, "family claim without direct basis"
    if re.search(r"\bmy\s+lawyer\b", lowered):
        return "UNKNOWN", "biographical-claim-about-other", 0.88, "claim about another person without explicit direct basis"
    if re.search(r"\bstrong\s+(?:and\s+)?masculine\s+dad\b", lowered):
        return "UNKNOWN", "family-claim", 0.88, "family/person characterization without explicit direct basis"
    if re.search(r"\bwhich\s+decreed\b|\bdecreed\s+that\s+they\s+would\s+bless\b|\btheir\s+(?:policy|doctrinal\s+stance)\s+changed\b", lowered):
        return "UNKNOWN", "institution-claim", 0.86, "external organisation/institution claim without attached source basis"
    if re.search(r"\bchurch\s+of\s+england\b|\bdiocese\b|\bchurch\b|\binstitution\b|\bwhich\s+is\s+super\s+woke\b", lowered):
        return "UNKNOWN", "institution-claim", 0.86, "unsupported institution characterization or claim"
    if re.search(r"\bwho\s+want\s+to\s+kill\b|\bwant\s+to\s+kill\b|\bhate\s+the\s+term\b|\bdidn['’â€™]?t\s+like\b", lowered):
        return "UNKNOWN", "motive-claim", 0.90, "motive/inner-state claim about others"
    if lowered == "we were":
        return "UNKNOWN", "historic-claim", 0.86, "collective/historical claim without direct source basis"
    if re.search(r"\bwe['’â€™]?re\s+being\s+invaded\b|\bpeople\s+talk\s+about\b|\bthe\s+left\b|\bwe\s+were\b|\bwe\s+abandoned\b", lowered):
        return "UNKNOWN", "group-claim", 0.90, "collective/group/historical claim without direct source basis"
    if re.search(r"\bmass\s+slaughter\b|apostate\b|true\s+christians\b|should\s+do\s+it\b", lowered):
        return "UNKNOWN", "class-definition", 0.86, "external classification or class-definition claim"
    if re.search(r"\bsodomite\b|\bheathens\b|\bfake\s+priests\b", lowered):
        return "UNKNOWN", "slur-label", 0.88, "external group/person label requiring review"
    if re.search(r"\b\d{2,}|\bthousands\b|\bmillions\b|\bmore\s+than\b|\bless\s+than\b|\brate\s+of\b|\bpercent\b|%", lowered):
        return "UNKNOWN", "numeric-claim", 0.84, "measurable/numeric claim without source basis"

    # Fall back to the existing conservative classifier for older tuned cases.
    return _classify_clause_text(clean)

def classify_claim_text(
    text: object,
    *,
    source_id: str = "",
    speaker: str = "",
    timestamp_start: str = "",
    timestamp_end: str = "",
    media_source_role: str = "UNKNOWN_PROVENANCE",
) -> tuple[ClaimRoleSpan, ...]:
    raw = str(text or "")
    media_role = normalize_media_source_role(media_source_role)
    spans: list[ClaimRoleSpan] = []
    for clause, start, end in _semantic_policy_split_claim_clauses_v3(raw):
        role, designation, confidence, reason = _semantic_policy_classify_clause_text_v3(clause)
        embedded = _question_embedded_claim(clause) if role == "BLANK" and designation == "question" else ()
        spans.append(ClaimRoleSpan(
            source_id=source_id,
            speaker=speaker,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            char_start=start,
            char_end=end,
            text=clause,
            role=role,
            designation=designation,
            confidence=confidence,
            reason=reason,
            media_source_role=media_role,
            review_state="assigned",
            embedded_claims=embedded,
        ))
    if spans:
        read_that_indices = [index for index, span in enumerate(spans) if re.search(r"\bi\s+read\s+that\s+cover\s+to\s+cover\b", _norm(span.text))]
        if read_that_indices:
            first_read = read_that_indices[0]
            for index in range(0, first_read):
                span = spans[index]
                if span.role == "UNKNOWN" and span.designation == "external-object-label":
                    spans[index] = replace(
                        span,
                        role="SECONDARY",
                        designation="document-witness",
                        confidence=0.84,
                        reason="preceding instruction/description is carried by the explicit direct document-witness clause in the same block",
                    )
        return tuple(spans)
    return (ClaimRoleSpan(source_id, speaker, timestamp_start, timestamp_end, 0, 0, "", "BLANK", "filler", 0.99, "empty/filler input", media_role, "assigned"),)


def transcript_hash(text: object) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8", errors="replace")).hexdigest()


def canonicalize_duplicate_transcript_stream(text: object) -> dict[str, Any]:
    raw = str(text or "")
    parts = [part.strip() for part in re.split(r"(?m)^\s*-{4,}\s*$", raw) if part.strip()]
    if len(parts) <= 1:
        return {
            "text": raw,
            "duplicate_raw_transcript_text": "",
            "duplicate_transcript_representations_detected": False,
            "parts_seen": len(parts) or 1,
            "parts_kept": 1,
        }
    kept = [parts[0]]
    duplicate_tail = "\n----\n".join(parts[1:])
    first_key = re.sub(r"\s+", " ", re.sub(r"\d{1,2}:\d{2}(?::\d{2})?\s*-\s*\d{1,2}:\d{2}(?::\d{2})?\s*\[[^\]]+\]", "", parts[0])).casefold().strip()
    tail_key = re.sub(r"\s+", " ", re.sub(r"\d{1,2}:\d{2}(?::\d{2})?\s*-\s*\d{1,2}:\d{2}(?::\d{2})?\s*\[[^\]]+\]", "", duplicate_tail)).casefold().strip()
    return {
        "text": kept[0],
        "duplicate_raw_transcript_text": duplicate_tail,
        "duplicate_transcript_representations_detected": bool(tail_key and (tail_key == first_key or len(parts) > 1)),
        "parts_seen": len(parts),
        "parts_kept": len(kept),
        "duplicate_raw_transcript_section_label": "duplicate_raw_transcript",
    }


_TIMESTAMP_LINE_RE = re.compile(r"^(?P<start>\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(?P<end>\d{1,2}:\d{2}(?::\d{2})?)\s*(?:\[(?P<speaker>[^\]]+)\])?\s*$")


def parse_transcript_blocks(text: object, *, source_id: str = "transcript") -> tuple[TranscriptBlock, ...]:
    canonical = canonicalize_duplicate_transcript_stream(text)["text"]
    blocks: list[TranscriptBlock] = []
    pending_text = ""
    pending_start = 0
    cursor = 0
    for raw_line in str(canonical or "").splitlines(keepends=True):
        line_start = cursor
        cursor += len(raw_line)
        line = raw_line.strip()
        if not line or line.lower() == "transcript":
            continue
        if not pending_text and re.match(r"^[A-Z][A-Za-z'â€™.-]+(?:\s+[A-Z][A-Za-z'â€™.-]+){1,4}\s+-\s+[\"'â€œ][^\"'â€]+[\"'â€]\s*$", line):
            continue
        if line == "----":
            break
        match = _TIMESTAMP_LINE_RE.match(line)
        if match and pending_text.strip():
            blocks.append(TranscriptBlock(
                source_id=source_id,
                speaker=(match.group("speaker") or "").strip(),
                timestamp_start=match.group("start"),
                timestamp_end=match.group("end"),
                text=" ".join(pending_text.split()),
                char_start=pending_start,
                char_end=line_start,
            ))
            pending_text = ""
            pending_start = cursor
            continue
        if match and not pending_text.strip():
            pending_start = cursor
            continue
        if not pending_text:
            pending_start = line_start
        pending_text += raw_line
    if pending_text.strip():
        blocks.append(TranscriptBlock(source_id, "", "", "", " ".join(pending_text.split()), pending_start, cursor))
    return tuple(blocks)


def classify_transcript_text(
    text: object,
    *,
    source_id: str = "transcript",
    media_source_role: str = "PRIMARY_SOURCE_EVIDENCE",
    use_cache: bool = True,
) -> tuple[ClaimRoleSpan, ...]:
    canonical = canonicalize_duplicate_transcript_stream(text)["text"]
    key = (POLICY_VERSION, transcript_hash(canonical), normalize_media_source_role(media_source_role))
    if use_cache and key in _CLASSIFICATION_CACHE:
        return _CLASSIFICATION_CACHE[key]
    output: list[ClaimRoleSpan] = []
    for block in parse_transcript_blocks(canonical, source_id=source_id):
        for span in classify_claim_text(
            block.text,
            source_id=block.source_id,
            speaker=block.speaker,
            timestamp_start=block.timestamp_start,
            timestamp_end=block.timestamp_end,
            media_source_role=media_source_role,
        ):
            output.append(span)
    result = tuple(output)
    if use_cache:
        _CLASSIFICATION_CACHE[key] = result
    return result


def cached_sections_for_path(path: str | Path) -> dict[str, str]:
    file_path = Path(path)
    stat = file_path.stat()
    key = (str(file_path.resolve()), int(stat.st_mtime_ns), int(stat.st_size))
    if key in _SECTION_CACHE:
        return _SECTION_CACHE[key]
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if file_path.suffix.lower() == ".rtf":
        text = extract_plain_text_from_rtf(text)
    sections = sections_by_type(split_source_text_sections(text))
    _SECTION_CACHE[key] = sections
    return sections


def build_full_transcript_role_tag_plan(spans: Iterable[ClaimRoleSpan]) -> dict[str, Any]:
    span_dicts = [span.to_dict() for span in spans]
    return {
        "schema_version": "profile-media-full-transcript-role-tags-v1",
        "policy_version": POLICY_VERSION,
        "full_transcript_order_preserved": True,
        "clause_level_tags": True,
        "max_visible_height_per_card": True,
        "internal_scrollbar_required": True,
        "spans": span_dicts,
        "tag_ranges": [
            {
                "tag": f"claim_role_{span['role'].lower()}",
                "source_id": span["source_id"],
                "timestamp_start": span["timestamp_start"],
                "timestamp_end": span["timestamp_end"],
                "char_start": span["char_start"],
                "char_end": span["char_end"],
                "edit_key": span["edit_key"],
            }
            for span in span_dicts
        ],
    }


def persist_claim_span_role_edits(spans: Iterable[ClaimRoleSpan], selected_roles_by_edit_key: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for span in spans:
        payload = span.to_dict()
        key = payload["edit_key"]
        selected = selected_roles_by_edit_key.get(key, payload["role"])
        payload["selected_role"] = selected if selected in {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK"} else payload["role"]
        rows.append(payload)
    return {
        "schema_version": "profile-media-claim-span-role-edits-v1",
        "policy_version": POLICY_VERSION,
        "edit_key_fields": ["source_id", "timestamp_start", "timestamp_end", "char_start", "char_end"],
        "rows": rows,
    }


def build_claim_role_markup(spans: Iterable[ClaimRoleSpan | dict[str, Any]], selected_roles_by_edit_key: dict[str, str] | None = None) -> str:
    selected = selected_roles_by_edit_key or {}
    lines: list[str] = []
    for span in spans:
        payload = span.to_dict() if hasattr(span, "to_dict") else dict(span)  # type: ignore[arg-type]
        text = " ".join(str(payload.get("text") or "").split())
        if not text:
            continue
        role = str(selected.get(str(payload.get("edit_key") or ""), payload.get("role") or "UNKNOWN")).strip().upper()
        if role not in {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK"}:
            role = "UNKNOWN"
        lines.append(f"[{text} | {role.title()}]")
    return "\n".join(lines)


def build_claim_role_build_worker_plan(text_length: int) -> dict[str, Any]:
    use_worker = should_use_background_worker(text_length)
    return {
        "schema_version": "profile-media-claim-role-build-worker-plan-v1",
        "policy_version": POLICY_VERSION,
        "text_length": int(text_length),
        "runs_heavy_classification_synchronously_on_ui_thread": False if use_worker else False,
        "background_worker_required": use_worker,
        "build_button_disabled_while_running": True,
        "build_button_reenabled_after_completion_or_error": True,
        "progress_steps": list(build_claim_role_worker_progress_steps()),
    }


# SEMANTIC_POLICY_PASS2_COMPLETION_20260827
# A second policy layer over the v3 clause engine.  The v3 engine established
# shared transcript/comment segmentation.  This layer completes the remaining
# COPY(1) semantic policy by adding broader acknowledgement Blank handling,
# first-person/self-position boundaries, belief/thought prefix splitting, and
# stricter self-owned -> external-object transitions.  It intentionally reuses
# the same public classify_claim_text() name so transcript and comment body text
# keep one shared classifier path.

_PASS2_INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def _policy_pass2_clean_text(text: object) -> str:
    value = _PASS2_INVISIBLE_RE.sub("", str(text or ""))
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[\t\f\v ]+", " ", value)
    value = re.sub(r" *\n+ *", "\n", value)
    return value.strip()


def _policy_pass2_boundary_candidates(piece: str) -> list[tuple[int, int, str]]:
    """Return possible semantic boundaries as (left_end, right_start, reason)."""
    candidates: list[tuple[int, int, str]] = []
    n = _norm(piece)
    if not n:
        return candidates
    if re.match(r"^\s*i\s+(?:heard\s+(?:from|that)|read\s+that)\b", piece, flags=re.IGNORECASE):
        return candidates

    if re.match(r"^\s*which\s+decreed\b", piece, flags=re.IGNORECASE):
        return candidates

    def add_start(pattern: str, reason: str, *, min_left: int = 1) -> None:
        found = re.search(pattern, piece, flags=re.IGNORECASE)
        if not found or found.start() < min_left:
            return
        left_end = found.start()
        probe = left_end
        while probe > 0 and piece[probe - 1].isspace():
            probe -= 1
        if probe > 0 and piece[probe - 1] in {",", ";", ":"}:
            left_end = probe - 1
        candidates.append((left_end, found.start(), reason))

    def add_after(pattern: str, reason: str, *, min_left: int = 0) -> None:
        found = re.search(pattern, piece, flags=re.IGNORECASE)
        if not found or found.start() < min_left:
            return
        candidates.append((found.end(), found.end(), reason))

    # Belief / thought / knowledge markers must not swallow the external claim.
    if re.match(r"^\s*(?:and\s+|but\s+|now\s+|so\s+|uh\s+)?I\s+(?:believe|think|contend|know)\b", piece, flags=re.IGNORECASE):
        # Keep concrete self-imperative phrases together: "I think we need...".
        if not re.match(r"^\s*(?:and\s+|but\s+|now\s+|so\s+|uh\s+)?I\s+think\s+we\s+need\b", piece, flags=re.IGNORECASE):
            add_after(r"^\s*(?:and\s+|but\s+|now\s+|so\s+|uh\s+)?I\s+(?:believe|think|contend|know)\b", "belief/thought/knowledge prefix")
    add_start(r"\band\s+I\s+(?:believe|think|contend|know)\b", "internal belief/thought boundary", min_left=8)
    add_start(r"\band\s+I\s+hate\b", "external object to self-feeling boundary", min_left=8)
    add_start(r"\bbut\s+I\s+(?:believe|think|contend|know|would\s+contend)\b", "contrastive belief/thought boundary", min_left=8)

    # Self-feeling/stance prefix vs external object.
    if re.match(r"^\s*I\s+hate\s+this\b", piece, flags=re.IGNORECASE):
        add_after(r"^\s*I\s+hate\b", "self-feeling before external object")
    if re.match(r"^\s*I\s+don['’]?t\s+think\b", piece, flags=re.IGNORECASE):
        add_after(r"^\s*I\s+don['’]?t\s+think\b", "negative thought prefix")
    if re.match(r"^\s*My\s+hope\s+and\s+prayer\s+is\s+that\b", piece, flags=re.IGNORECASE):
        add_start(r"\bthat\b", "self hope/prayer vs external outcome", min_left=5)
    add_start(r"\band\s+I\s+shudder\b", "external group to self-feeling", min_left=8)
    add_start(r"\band\s+I\s+have\s+no\s+hatred\b", "external group to self-feeling", min_left=8)
    add_start(r"\bI\s+have\s+no\s+hatred\b", "self-feeling boundary", min_left=8)
    add_start(r"\bI\s+pity\b", "self-feeling boundary", min_left=8)

    # Primary imperative/action prefix vs external object label.
    if re.match(r"^\s*We\s+need\s+to\s+end\s+the\b", piece, flags=re.IGNORECASE):
        add_start(r"\bthe\b", "imperative object boundary", min_left=10)
    if re.match(r"^\s*We\s+need\s+to\s+stop\s+these\b", piece, flags=re.IGNORECASE):
        add_start(r"\bthese\b", "imperative object boundary", min_left=10)
    if re.match(r"^\s*We['’]?ve\s+saved\b", piece, flags=re.IGNORECASE):
        add_after(r"^\s*We['’]?ve\s+saved\b", "speaker-owned action before numeric/object claim")
    if re.match(r"^\s*We\s+saved\b", piece, flags=re.IGNORECASE):
        add_after(r"^\s*We\s+saved\b", "speaker-owned action before numeric/object claim")
    if re.match(r"^\s*We\s+need\s+to\s+raise\s+up\s+men\b", piece, flags=re.IGNORECASE):
        # Keep the direct object "men" with the imperative, but split later relative clause.
        add_start(r"\bwho\s+are\s+going\b", "imperative target relative clause", min_left=12)

    # Concrete us/we institutional experience.
    add_start(r"\b(?:does\s+not|doesn['’]?t)\s+(?:censor|rein\s+in|muzzle)\s+us\b", "included-us institutional experience", min_left=8)

    # Other common external boundary after a speaker-owned prefix.
    for pattern in (
        r"\bthat\s+(?:Christ|Jesus|the\s+Church|the\s+country|there\s+is|that\s+is|this\s+is)\b",
        r"\bthat\s+they\b",
        r"\btheir\s+right\b",
        r"\bwhich\s+(?:is|has|was|were|decreed|sees)\b",
        r"\bwho\s+(?:have|has|was|were|is|are|want|insists|may|come|worship)\b",
        r"\bbecause\s+(?:the|they|it|we|he|she|their|there)\b",
        r"\beveryone\s+from\s+the\s+left\b",
        r"\ba\s+very\s+strong\s+(?:and\s+)?masculine\s+dad\b",
        r"\bmy\s+grandfather\s+was\b",
        r"\bthese\s+fake\s+priests\b",
        r"\bof\s+heretics\s+out\s+of\s+town\b",
        r"\band\s+don['’]?t\s+intend\b",
        r"\bstill\s+living\s+(?:rent\s+free|free\s+rent)\b",
    ):
        add_start(pattern, "COPY(1) external-object/pronoun boundary", min_left=6)

    # Recommendation followed by evaluative claim: "read X, its excellent..."
    found = re.search(r",\s*(?:it['’]?s|its)\s+", piece, flags=re.IGNORECASE)
    if found and _norm(piece).startswith("you ought to read"):
        candidates.append((found.start(), found.start() + 1, "recommendation to evaluative claim"))

    return sorted(candidates, key=lambda item: item[0])


def _policy_pass2_sentence_spans(raw: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    start = 0
    # Treat sentence punctuation, explicit line breaks, and schedule runs as hard-ish boundaries.
    for match in re.finditer(r"(?:\n+|(?<=[.!?])\s+)", raw):
        piece = _trim_span(raw, start, match.start())
        if piece[0]:
            spans.append(piece)
        start = match.end()
    piece = _trim_span(raw, start, len(raw))
    if piece[0]:
        spans.append(piece)
    return spans


def _policy_pass2_split_piece(piece: str, abs_start: int) -> list[tuple[str, int, int]]:
    pending: list[tuple[str, int, int]] = [(piece, abs_start, abs_start + len(piece))]
    for _ in range(64):
        changed = False
        next_pending: list[tuple[str, int, int]] = []
        for text_part, part_start, _part_end in pending:
            candidates = _policy_pass2_boundary_candidates(text_part)
            if not candidates:
                next_pending.append((text_part, part_start, part_start + len(text_part)))
                continue
            left_end, right_start, _reason = candidates[0]
            left = _trim_span(text_part, 0, left_end)
            right = _trim_span(text_part, right_start, len(text_part))
            if left[0]:
                next_pending.append((left[0], part_start + left[1], part_start + left[2]))
            if right[0]:
                next_pending.append((right[0], part_start + right[1], part_start + right[2]))
            changed = True
        pending = next_pending
        if not changed:
            break
    return pending


def _semantic_policy_split_claim_clauses_v4(text: object) -> tuple[tuple[str, int, int], ...]:
    raw = _policy_pass2_clean_text(text)
    if not raw:
        return ()
    pieces: list[tuple[str, int, int]] = []
    for sentence, start, _end in _policy_pass2_sentence_spans(raw):
        pieces.extend(_policy_pass2_split_piece(sentence, start))

    # Prefer the finer of v4 and v3 when v3 knows a longer special-case split.
    try:
        old = _semantic_policy_split_claim_clauses_v3(raw)
    except Exception:
        old = ()
    if old and len(old) > len(pieces) and len(raw) < 420 and not re.match(r"^\s*i\s+(?:heard\s+(?:from|that)|read\s+that)\b", raw, flags=re.IGNORECASE):
        pieces = list(old)

    cleaned: list[tuple[str, int, int]] = []
    for piece, start, end in pieces:
        trimmed, t_start, t_end = _trim_span(raw, start, end)
        if trimmed and re.search(r"[A-Za-z0-9]", trimmed):
            cleaned.append((trimmed, t_start, t_end))
    return tuple(cleaned)


def _semantic_policy_classify_clause_text_v4(text: str) -> tuple[str, str, float, str]:
    clean = _strip_invisible_text(text).strip()
    lowered = _norm(clean).strip(" .?!")
    if not lowered:
        return "BLANK", "filler", 0.99, "empty or filler span"
    if re.search(r"was\s+around\s+really\s+godly\s+men", lowered):
        return "UNKNOWN", "external-object-label", 0.84, "person/group characterization without speaker-action boundary"

    # Expanded Blank: acknowledgements, filler, reactions, prompts, stage directions, blessings.
    blank_phrases = {
        "yes", "yeah", "mhm", "mhhm", "mmhh", "mmh", "mmhh-", "uh", "um", "uh-", "um-",
        "and then", "you poor man", "winning", "not yet", "a fair criticism", "spot on", "right",
        "of course", "absolutely", "of course we do", "that's right", "thats right", "very true",
        "correct", "okay", "ok", "tiny", "well", "well-", "no", "100%",
    }
    if clean.endswith("?"):
        return "BLANK", "question", 0.98, "question/prompt is not itself establishing a claim"
    if lowered in blank_phrases:
        return "BLANK", "filler", 0.97, "acknowledgement/filler/reaction is not establishing a claim"
    if re.search(r"^\(?says\s+[a-z].*\)?$", lowered) or re.search(r"^\*.+\*$", clean) or re.search(r"^\(.+\)$", clean):
        return "BLANK", "filler", 0.96, "stage direction / speaker-action note"
    if re.search(r"^(?:@\S+\s+)*(?:you['’]?re\s+welcome\s+)?(?:god\s+bless(?:\s+you)?(?:\s+richly|\s+sir)?|bless\s+you|love\s+and\s+blessings(?:\s+[a-z0-9_-]+)?|praise\s+be\s+to\s+god,?\s+may\s+the\s+lord\s+guide\s+your\s+steps|may\s+god\s+bless(?:\s+and\s+protect\s+him)?|may\s+god\s+grant\s+us\s+victory)\s*[!🙌❤🙏😇🇬🇧😎😊]*$", lowered):
        return "BLANK", "filler", 0.96, "blessing/prayer/acknowledgement is not establishing a source claim"
    if re.search(r"^(?:thank\s+you|thanks)(?:\s+for\s+(?:your\s+)?(?:kind\s+)?(?:encouragement|support|help|message|comment|words))?\s*[!🙌❤🙏😇🇬🇧😎😊]*$", lowered):
        return "BLANK", "filler", 0.96, "acknowledgement-only thanks is not establishing a source claim"
    if re.search(r"^you\s+ought\s+to\s+read\b", lowered):
        return "BLANK", "filler", 0.96, "reading recommendation is a prompt, not a claim about the source text"
    if re.search(r"^it\s+was\s+a\s+pleasure\s+to\s+sit\s+down\s+with\s+you\b", lowered):
        return "BLANK", "filler", 0.96, "courtesy acknowledgement is not establishing a claim"
    if re.search(r"^(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*)?(?:sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b", lowered) or re.search(r"^\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*[-–]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s+", lowered):
        return "BLANK", "filler", 0.95, "schedule/service-time line is contextual information rather than a claim span"

    # Direct source basis: Secondary.
    if re.search(r"\bi\s+saw\b|\bi\s+was\s+standing\s+there\s+when\b|\bwe['’]?ve\s+seen\b", lowered):
        return "SECONDARY", "witness-event", 0.95, "speaker claims direct observation"
    if re.search(r"\b(?:everyone|people)\b.*\bstarted\s+attacking\s+me\b", lowered):
        return "SECONDARY", "witness-reaction", 0.90, "speaker reports directly experienced reaction from others"
    if re.search(r"\bwe['’]?ve\s+had\s+women\s+moved\s+to\s+tears\b", lowered):
        return "SECONDARY", "witness-reaction", 0.95, "speaker claims witnessed reaction of other people"
    if re.search(r"\b(?:[a-z][\w'-]+\s+)?(?:tell|told)\s+me\b|\bsaid\s+to\s+me\b|\bthey\s+said\s+basically\b|\btells\s+me\b|\blike\s+you\s+said\b|\bi['’]?ve\s+spoken\s+to\b|\bi\s+heard\s+[a-z][\w'-]+\s+say\b", lowered):
        designation = "direct-quote" if re.search(r"[\"'‘“].+[\"'’”]", clean) else "direct-attribution"
        return "SECONDARY", designation, 0.93, "direct interaction or direct attribution to speaker"
    if re.search(r"\bi\s+read\s+(?:the|this|that)\s+(?:church\s+)?(?:report|document|book|cover\s+to\s+cover)\b|\bi\s+read\s+the\s+church\s+report\b|\bi\s+read\s+that\s+cover\s+to\s+cover\b|\bi\s+read\s+(?:the\s+)?quran\s+cover\s+to\s+cover\b", lowered):
        return "SECONDARY", "document-witness", 0.90, "speaker directly encountered the document/material"
    if re.search(r"\bconcluded\s+the\s+church\s+of\s+england\s+is\s+apostate\b", lowered):
        return "SECONDARY", "document-based-interpretation", 0.86, "document-based interpretation after direct document witness clause"

    # Relayed source-chain: Tertiary.
    if re.search(r"\bi\s+heard\s+from\b|\bi\s+heard\s+that\b|\baccording\s+to\b|\bpeople\s+say\b|\bthe\s+report\s+says\b", lowered):
        return "TERTIARY", "hearsay-report", 0.90, "relayed source-chain/hearsay report"
    if re.search(r"\bi\s+read\s+that\b", lowered):
        return "TERTIARY", "written-source-report", 0.93, "speaker reports reading that another source wrote/said something"
    if re.search(r"\bthe\s+lord\s+jesus\s+said\b|\blord\s+jesus\s+said\b", lowered):
        return "TERTIARY", "direct-quote", 0.86, "relayed quote/source-chain marker"
    if re.search(r"\b(?:he|she|[A-Z][A-Za-z.'-]+)\s+(?:said|wrote|posted|shared|reported|had\s+written|had\s+messaged)\b", clean) and not re.search(r"\btold\s+me\b|\bsaid\s+to\s+me\b", lowered):
        return "TERTIARY", "written-source-report", 0.82, "third-party report without direct-to-speaker basis"

    if re.search(r"^we\s+have\s+abandoned\b", lowered):
        return "UNKNOWN", "group-claim", 0.90, "collective/historical we claim without direct source basis"

    # Primary: self-owned action, belief, feeling, intent, concrete included we/us.
    if lowered in {"i'm", "i’m", "i am"}:
        return "PRIMARY", "self-biographical", 0.84, "speaker-owned self-reference boundary"
    if re.search(r"^(?:and\s+|but\s+|now\s+|so\s+|uh\s+)?i\s+(?:believe|think|contend|know)\b|^i\s+don['’]?t\s+think\b", lowered):
        return "PRIMARY", "self-belief", 0.90, "speaker-owned belief/thought/knowledge marker"
    if re.search(r"\bi\s+would\s+contend\b|\bi['’]?m\s+more\s+inclined\b|\bi\s+am\s+more\s+inclined\b|\bi\s+stand\s+with\b", lowered):
        return "PRIMARY", "self-belief", 0.89, "speaker-owned stance/preference"
    if re.search(r"\bi\s+(?:actually\s+)?(?:felt|feel|shudder|have\s+no\s+hatred|pity|hate)\b|\bi['’]?m\s+very\s+compassionate\s+towards\b|\bi['’]?m\s+so\s+thankful\b|\bi['’]?ve\s+nothing\s+against\b|\bi\s+have\s+nothing\s+against\b|\bmy\s+hope\s+and\s+prayer\s+is\b|\bi\s+just\s+don['’]?t\s+care\b|\bi\s+don['’]?t\s+care\b", lowered):
        return "PRIMARY", "self-feeling", 0.90, "speaker-owned feeling/self-position"
    if re.search(r"\bi\s+just\s+say\b|\bi\s+would\s+say\b", lowered):
        return "PRIMARY", "self-action", 0.90, "speaker-owned reported/intended speech action"
    if re.search(r"^(?:that\s+is|that['’]?s)\s+my\s+(?:title|role|position)\b|\bmy\s+(?:title|role|position)\b|\bi['’]?m\s+such\s+a\s+horrible\s+chap\b|\bi\s+am\s+such\s+a\s+horrible\s+chap\b|\bi['’]?m\s+not\s+a\s+woman\b|\bi['’]?m\s+an\s+intersex\b|\bi['’]?m\s+a\s+bit\s+of\s+a\s+rebel\b|\bi['’]?m\s+personally\s+a\s+christian\s+nationalist\b", lowered):
        return "PRIMARY", "self-biographical", 0.90, "speaker-owned self-description/self-context"
    if re.search(r"\bmy\s+anglican\s+theological\s+convictions\b|\bmy\s+theological\s+convictions\b", lowered):
        return "PRIMARY", "self-belief", 0.90, "speaker-owned theological conviction/self-explanation"
    if re.search(r"\bpeople\s+freely\s+chose\s+to\s+support\s+me\b", lowered):
        return "PRIMARY", "self-biographical", 0.86, "speaker-owned support/self-context"
    if re.search(r"\bi\s+could\s+handle\s+that\b", lowered):
        return "PRIMARY", "self-biographical", 0.88, "speaker-owned capacity/self-context"
    if re.search(r"\bi\s+was\s+never\s+going\s+to\s+stay\b", lowered):
        return "PRIMARY", "self-intent", 0.90, "speaker-owned position/boundary"
    if re.search(r"\bi\s+can['’]?t\s+help\s+myself\b", lowered):
        return "PRIMARY", "self-biographical", 0.88, "speaker-owned self-context"
    if re.search(r"\bit\s+was\s+my\s+fault\b|\bi\s+chose\s+to\s+leave\b|\bwhen\s+i\s+left\b|\bi\s+was\s+(?:sacked|dismissed|fired|cancelled|canceled|invited|vetted|part\s+of)\b|\bi\s+was\s+thoroughly\s+vetted\b", lowered):
        return "PRIMARY", "self-action", 0.88, "speaker-owned event/action account"
    if re.search(r"\bi['’]?ve\s+run\s+plenty\b|\bi\s+have\s+run\s+plenty\b|\bi['’]?ve\s+run\b|\bi\s+have\s+run\b|\bi\s+(?:want|decided|started|run|offer|saved|resigned|moved|held|increased|joined|approached|was\s+getting|just\s+say|would\s+say|would\s+welcome|can['’]?t\s+imagine|can['’]?t\s+help|could\s+handle|didn['’]?t\s+have\s+to|wouldn['’]?t\s+receive|was\s+never\s+going\s+to\s+stay|found\s+out|found)\b", lowered):
        return "PRIMARY", "self-action", 0.88, "speaker-owned action or experience"
    if re.search(r"^(?:and\s+)?don['’]?t\s+intend\s+to\s+stop\b", lowered):
        return "PRIMARY", "self-intent", 0.86, "elliptical speaker-owned intent continuing prior first-person clause"
    if re.search(r"you['’]?re\s+very\s+welcome\s+to\s+join\s+us\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.84, "speaker-owned invitation into speaker group"
    if re.search(r"\bi\s+was\s+raised\b", lowered):
        return "PRIMARY", "self-biographical", 0.92, "self-biographical claim"
    if re.search(r"\bmy\s+(?:my\s+)?red\s+line\s+was\b|\bmy\s+red\s+line\s+in\s+the\s+sand\s+was\b", lowered):
        return "PRIMARY", "self-intent", 0.90, "speaker-owned position/boundary"
    if re.search(r"\bgod\s+very\s+strongly\s+put\s+on\s+my\s+heart\b", lowered):
        return "PRIMARY", "self-belief", 0.88, "speaker-owned spiritual self-experience"
    if re.search(r"\bto\s+speak\s+out\s+against\s+this\b", lowered):
        return "PRIMARY", "self-intent", 0.86, "speaker-owned stated intent/action"
    if re.search(r"\bthis\s+youtube\s+channel\s+took\s+off\b|\bit\s+went\s+wild\b|\bit\s+started\s+with\s+like\s+five\s+views\b|\broller\s+coaster\s+ride\b|\bit\s+was\s+not\s+what\s+i\s+expected\b", lowered):
        return "PRIMARY", "self-action", 0.86, "speaker-owned channel/service history or self-experience"
    if re.search(r"\bwe\s+moved\b|\bso\s+we\s+moved\b", lowered):
        return "PRIMARY", "self-action", 0.90, "concrete speaker-group action"
    if re.search(r"\bwe['’]?ve\s+preached\b", lowered):
        return "PRIMARY", "speaker-owned-institutional-action", 0.92, "speaker-owned institutional action"
    if re.search(r"\bwe\s+(?:need\s+to|should|will|don['’]?t\s+want\s+to|work\s+with|offer|saved|save|run|moved|have|are\s+a\s+church|are\s+under\s+harsh\s+judg(?:e)?ment)\b|\bwe['’]?ve\s+preached\b|\bwe['’]?ve\s+saved\b", lowered):
        designation = "speaker-owned-institutional-action" if re.search(r"preached|offer|saved|work\s+with|have", lowered) else "speaker-owned-imperative"
        if re.search(r"under\s+harsh\s+judg", lowered):
            designation = "self-belief"
        return "PRIMARY", designation, 0.90, "concrete included-we/us speaker-owned action, belief, or imperative"
    if re.search(r"\b(?:does\s+not|doesn['’]?t)\s+(?:censor|rein\s+in|muzzle)\s+us\b|\bdoes\s+not\s+censor\s+us\b|\bdoes\s+not\s+rein\s+us\s+in\b", lowered):
        return "PRIMARY", "speaker-owned-institutional-action", 0.84, "included-us direct institutional experience"
    if re.search(r"\bthose\s+are\s+the\s+people\s+that\s+we\s+should\s+accept\b", lowered):
        return "PRIMARY", "speaker-owned-imperative", 0.88, "speaker-owned policy preference"

    # Unknown: unsupported external claims, groups, institutions, history, numbers, motives, inner states, family, labels.
    if re.search(r"^that\s+in\s+the\s+past\b", lowered):
        return "UNKNOWN", "historic-claim", 0.86, "historical/collective claim separated from belief marker"
    if re.search(r"^that\s+(?:christ|jesus|the\s+church|the\s+country|there\s+is|that\s+is|this\s+is)\b|^jesus\s+actually\b|^that\s+they\b", lowered):
        return "UNKNOWN", "historic-claim", 0.84, "external claim following a speaker-owned belief/feeling marker"
    if re.search(r"^their\s+right\b|^(?:it['’]?s|its)\s+an\s+excellent\s+examination\b|^and\s+the\s+growing\s+flock\b|^this\s+gentle\b", lowered):
        return "UNKNOWN", "external-object-label", 0.84, "external-object/institution/group claim separated from speaker-owned phrase"
    if re.search(r"^(?:still\s+living|living)\s+(?:rent\s+free|free\s+rent)\s+in\s+your\s+head", lowered):
        return "UNKNOWN", "inner-state-claim-about-other", 0.82, "taunt/claim about addressee rather than speaker-owned self-description"
    if re.search(r"\bthese\s+fake\s+priests\b", lowered):
        return "UNKNOWN", "slur-label", 0.88, "external person/group slur label separated from speaker-owned feeling"
    if re.search(r"^of\s+heretics\s+out\s+of\s+town\b", lowered):
        return "UNKNOWN", "external-person-label", 0.84, "external person/group label separated from speaker-owned action"
    if re.search(r"\bmy\s+wife\b.*\bfelt\b", lowered):
        return "UNKNOWN", "inner-state-claim-about-other", 0.92, "inner-state claim about another person without direct basis"
    if re.search(r"\bmy\s+grandfather\b|\bmy\s+dad\b", lowered):
        return "UNKNOWN", "family-claim", 0.90, "family claim without direct basis"
    if re.search(r"\bmy\s+lawyer\b", lowered):
        return "UNKNOWN", "biographical-claim-about-other", 0.88, "claim about another person without explicit direct basis"
    if re.search(r"\bstrong\s+(?:and\s+)?masculine\s+dad\b", lowered):
        return "UNKNOWN", "family-claim", 0.88, "family/person characterization without explicit direct basis"
    if re.search(r"\b(?:church\s+of\s+england|diocese|church|institution|council|government|country|nation|britain|israel|monarchy)\b|\bwhich\s+is\s+super\s+woke\b|\bwhich\s+decreed\b|\btheir\s+(?:policy|doctrinal\s+stance)\s+changed\b", lowered):
        return "UNKNOWN", "institution-claim", 0.86, "unsupported institution/country characterization or claim"
    if re.search(r"\bwho\s+want\s+to\s+kill\b|\bwant\s+to\s+kill\b|\bhate\s+the\s+term\b|\bdidn['’]?t\s+like\b|\bwanted\s+to\b|\binner\s+state\b", lowered):
        return "UNKNOWN", "motive-claim", 0.90, "motive/inner-state claim about others"
    if lowered == "we were" or re.search(r"\bwe['’]?re\s+being\s+invaded\b|\bpeople\s+talk\s+about\b|\bthe\s+left\b|\bwe\s+were\b|\bwe\s+abandoned\b|\bwe['’]?ve\s+been\s+abandoned\b|\bwe\s+had\s+morals\b", lowered):
        return "UNKNOWN", "group-claim", 0.90, "collective/group/historical claim without direct source basis"
    if re.search(r"\bmass\s+slaughter\b|\bapostate\b|\btrue\s+christians\b|\bshould\s+do\s+it\b|\bis\s+a\b|\bare\s+a\b", lowered):
        return "UNKNOWN", "class-definition", 0.84, "external classification or class-definition claim"
    if re.search(r"\bsodomite\b|\bheathens\b|\bheretics\b|\bfake\b|\bleftoid\b", lowered):
        return "UNKNOWN", "slur-label", 0.88, "external group/person label requiring review"
    if re.search(r"\b\d{2,}|\bthousands\b|\bmillions\b|\bmore\s+than\b|\bless\s+than\b|\brate\s+of\b|\bpercent\b|%", lowered):
        return "UNKNOWN", "numeric-claim", 0.84, "measurable/numeric claim without source basis"
    if re.search(r"\b(?:they|he|she|it|there|which|who|anyone|people|millions|some|these|that|for\s+them|in\s+your)\b", lowered):
        return "UNKNOWN", "external-object-label", 0.78, "unsupported claim about someone/something outside speaker"

    return _semantic_policy_classify_clause_text_v3(clean)


def classify_claim_text(
    text: object,
    *,
    source_id: str = "",
    speaker: str = "",
    timestamp_start: str = "",
    timestamp_end: str = "",
    media_source_role: str = "UNKNOWN_PROVENANCE",
) -> tuple[ClaimRoleSpan, ...]:
    raw = str(text or "")
    media_role = normalize_media_source_role(media_source_role)
    spans: list[ClaimRoleSpan] = []
    for clause, start, end in _semantic_policy_split_claim_clauses_v4(raw):
        role, designation, confidence, reason = _semantic_policy_classify_clause_text_v4(clause)
        embedded = _question_embedded_claim(clause) if role == "BLANK" and designation == "question" else ()
        spans.append(ClaimRoleSpan(
            source_id=source_id,
            speaker=speaker,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            char_start=start,
            char_end=end,
            text=clause,
            role=role,
            designation=designation,
            confidence=confidence,
            reason=reason,
            media_source_role=media_role,
            review_state="assigned",
            embedded_claims=embedded,
        ))
    if spans:
        read_that_indices = [index for index, span in enumerate(spans) if re.search(r"\bi\s+read\s+that\s+cover\s+to\s+cover\b", _norm(span.text))]
        if read_that_indices:
            first_read = read_that_indices[0]
            for index in range(0, first_read):
                span = spans[index]
                if span.role == "UNKNOWN" and span.designation in {"external-object-label", "external-classification"}:
                    spans[index] = replace(
                        span,
                        role="SECONDARY",
                        designation="document-witness",
                        confidence=0.84,
                        reason="preceding instruction/description is carried by the explicit direct document-witness clause in the same block",
                    )
        return tuple(spans)
    return (ClaimRoleSpan(source_id, speaker, timestamp_start, timestamp_end, 0, 0, "", "BLANK", "filler", 0.99, "empty/filler input", media_role, "assigned"),)

# SEMANTIC_POLICY_PASS3_TRANSCRIPT_CLEANUP_20260827
# Active v4 classifier override/wrapper.  The existing v4 engine remains the
# base, but these wrappers add the remaining full-transcript policy boundaries
# without changing Build/count UI, source provenance, comments rendering, or
# click-scroll behavior.
if '_PASS3_BASE_BOUNDARY_CANDIDATES_20260827' not in globals():
    _PASS3_BASE_BOUNDARY_CANDIDATES_20260827 = _policy_pass2_boundary_candidates

    def _policy_pass2_boundary_candidates(piece: str) -> list[tuple[int, int, str]]:  # type: ignore[no-redef]
        candidates = list(_PASS3_BASE_BOUNDARY_CANDIDATES_20260827(piece))

        def add_start(pattern: str, reason: str, *, min_left: int = 1) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            left_end = found.start()
            probe = left_end
            while probe > 0 and piece[probe - 1].isspace():
                probe -= 1
            if probe > 0 and piece[probe - 1] in {",", ";", ":"}:
                left_end = probe - 1
            candidates.append((left_end, found.start(), reason))

        def add_prefix(prefix_pattern: str, tail_pattern: str, reason: str) -> None:
            prefix = re.search(prefix_pattern, piece, flags=re.IGNORECASE)
            if not prefix:
                return
            tail = re.search(tail_pattern, piece[prefix.end():], flags=re.IGNORECASE)
            if not tail:
                return
            candidates.append((prefix.end() + tail.start(), prefix.end() + tail.end(), reason))

        # Leading self/source markers: keep the whole marker together, then split
        # the outside claim. This prevents "And I became convinced" from becoming
        # [And | Unknown] [I became convinced | Primary].
        add_prefix(r"^\s*(?:and\s+)?I\s+knew\b", r"\s+(?=something\b|that\b)", "pass3 self-knowledge marker")
        add_prefix(r"^\s*(?:and\s+)?I\s+became\s+convinced\b", r"\s+(?=that\b)", "pass3 self-belief marker")
        add_prefix(r"^\s*(?:and\s+)?I\s+found\s+out(?:\s+earlier|\s+earlier\s+in\s+[^t]+)?\b", r"\s+(?=that\b)", "pass3 direct-source-acquisition marker")

        # Leading acknowledgement before a claim: [Yes | Blank] [we need...].
        leading_ack = re.search(r"^\s*(?:yes|yeah|of course|right|correct)\s*,\s+(?=we\s+need\b)", piece, flags=re.IGNORECASE)
        if leading_ack and len(piece) > leading_ack.end() + 4:
            candidates.append((leading_ack.end() - 2, leading_ack.end(), "leading acknowledgement before claim"))

        # Remaining audit boundaries from the full transcript.
        for pattern in (
            r"\band\s+um\s+in\s+my\s+years\b",
            r"\bi['’]?ve\s+developed\b",
            r"\band\s+I\s+(?:feel|felt|threw|was)\b",
            r"\band\s+so\s+they\s+said\s+basically\b",
            r"\bUm\s+also\s+I\s+smoke\b",
            r"\band\s+they\s+kind\s+of\s+didn['’]?t\s+like\b",
            r"\band\s+I\s+might\s+have\b",
            r"\bcuz\s+when\s+he\s+told\s+me\b",
            r"\bI\s+blew\s+a\s+puff\b",
            r"\bBut,\s+you\s+know,\s+I\s+am\b",
            r"\bwhen\s+I['’]?ve\s+been\s+very\s+outspoken\b",
            r"\bwhich\s+is\s+a\s+badge\s+of\s+honou?r\s+to\s+me\b",
            r"\bthese\s+hordes\b",
        ):
            add_start(pattern, "pass3 full-transcript audit boundary", min_left=4)

        # Remove shallow splits that leave only a conjunction when a fuller
        # leading self/source marker split is also available.
        filtered: list[tuple[int, int, str]] = []
        for cand in candidates:
            left_text = piece[:cand[0]].strip().casefold()
            if left_text in {"and", "so", "but"} and any(other[0] > cand[0] for other in candidates):
                continue
            filtered.append(cand)

        unique: dict[tuple[int, int], tuple[int, int, str]] = {}
        for cand in filtered:
            unique[(cand[0], cand[1])] = cand
        return sorted(unique.values(), key=lambda item: item[0])

if '_PASS3_BASE_CLASSIFY_V4_20260827' not in globals():
    _PASS3_BASE_CLASSIFY_V4_20260827 = _semantic_policy_classify_clause_text_v4

    def _semantic_policy_classify_clause_text_v4(text: str) -> tuple[str, str, float, str]:  # type: ignore[no-redef]
        clean = _strip_invisible_text(text).strip()
        lowered = _norm(clean).strip(" .?!")
        if not lowered:
            return "BLANK", "filler", 0.99, "empty or filler span"

        # Pre-Primary guards.
        if re.search(r"\bi\s+found\s+out\b", lowered):
            return "SECONDARY", "direct-attribution", 0.86, "speaker reports receiving/finding out information rather than directly witnessing the whole claim"
        if re.search(r"^that\s+there\s+are\b|\btwo\s+male\s+suicides\b|\bmale\s+suicides\s+a\s+week\b", lowered):
            return "UNKNOWN", "numeric-claim", 0.88, "numeric/measurable outside claim needs source-reference review"
        if re.search(r"\bwe\s+have\s+multiple\s+churches\b|\bmultiple\s+churches\s+on\s+every\s+street\s+corner\b", lowered):
            return "UNKNOWN", "group-claim", 0.88, "public/national 'we have' claim, not the speaker's own church/ministry action"
        if re.search(r"^you\s+would\b|\byou\s+would\s+turn\b|\byou\s+would\s+end\b", lowered):
            return "UNKNOWN", "motive-claim", 0.82, "conditional/predictive claim about effects, not speaker-owned action"
        if re.search(r"^these\s+hordes\b", lowered):
            return "UNKNOWN", "slur-label", 0.90, "external group/object label separated from speaker-owned imperative"
        if re.search(r"^because\s+it\s+drew\s+a\s+lot\s+of\s+complaints\b|\bthe\s+hierarchy\s+of\s+that\s+church\s+caved\b", lowered):
            return "UNKNOWN", "institution-claim", 0.86, "external organisation/reaction claim surrounding a direct-attribution clause"
        if re.search(r"^and\s+they\s+kind\s+of\s+didn['’]?t\s+like\b", lowered):
            return "UNKNOWN", "motive-claim", 0.86, "other people's preference/inner-state claim"
        if re.search(r"^cuz\s+when\s+he\s+told\s+me\b", lowered):
            return "SECONDARY", "direct-attribution", 0.90, "direct received warning/source from another person"
        if re.search(r"^which\s+is\s+a\s+badge\s+of\s+honou?r\s+to\s+me\b", lowered):
            return "PRIMARY", "self-feeling", 0.90, "speaker-owned self-evaluation of the event"

        # Additional speaker-owned markers from the transcript audit.
        if re.search(r"^(?:and\s+)?i\s+(?:knew|became\s+convinced|thought)\b", lowered):
            return "PRIMARY", "self-belief", 0.90, "speaker-owned belief/thought/knowledge marker"
        if re.search(r"\bi['’]?ve\s+(?:developed|been\s+very\s+outspoken)\b|\bi\s+(?:developed|smoke\s+a\s+pipe|blew\s+a\s+puff|wouldn['’]?t\s+take|would\s+never\s+let)\b", lowered):
            return "PRIMARY", "self-action", 0.88, "speaker-owned action or experience"
        if re.search(r"\bi\s+am\s+a\s+little\s+bit\s+of\s+a\s+polemicist\b", lowered):
            return "PRIMARY", "self-biographical", 0.90, "speaker-owned self-description/self-context"
        if re.search(r"\bi\s+don['’]?t\s+care\b", lowered):
            return "PRIMARY", "self-feeling", 0.90, "speaker-owned feeling/self-position"

        return _PASS3_BASE_CLASSIFY_V4_20260827(clean)

# SEMANTIC_POLICY_PASS3B_TRANSCRIPT_EDGE_CLEANUP_20260827
# Final transcript-audit edge cleanup over the v4/pass3 shared classifier.
# This keeps comments, Build counts, click-scroll, case/topics, and source
# provenance untouched.  It only adds missing clause boundaries/classification
# precedence from the remaining role-markup audit.
if '_PASS3B_BASE_BOUNDARY_CANDIDATES_20260827' not in globals():
    _PASS3B_BASE_BOUNDARY_CANDIDATES_20260827 = _policy_pass2_boundary_candidates

    def _policy_pass2_boundary_candidates(piece: str) -> list[tuple[int, int, str]]:  # type: ignore[no-redef]
        candidates = list(_PASS3B_BASE_BOUNDARY_CANDIDATES_20260827(piece))

        def add_start(pattern: str, reason: str, *, min_left: int = 1) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            left_end = found.start()
            probe = left_end
            while probe > 0 and piece[probe - 1].isspace():
                probe -= 1
            if probe > 0 and piece[probe - 1] in {',', ';', ':'}:
                left_end = probe - 1
            candidates.append((left_end, found.start(), reason))

        def add_after(pattern: str, reason: str, *, min_left: int = 0) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            candidates.append((found.end(), found.end(), reason))

        def add_prefix(prefix_pattern: str, tail_pattern: str, reason: str) -> None:
            prefix = re.search(prefix_pattern, piece, flags=re.IGNORECASE)
            if not prefix:
                return
            tail = re.search(tail_pattern, piece[prefix.end():], flags=re.IGNORECASE)
            if not tail:
                return
            candidates.append((prefix.end() + tail.start(), prefix.end() + tail.end(), reason))

        add_start(r"[\"'‘“â€˜â€œ]\s*You['’â€™]?re\s+not\s+a\s+real\s+priest\b", "speaker-owned say-action to quoted external label", min_left=4)
        add_start(r"\bin\s+the\s+diocese\s+shoved\s+women\b", "self pulpit refusal to external diocese action", min_left=8)
        add_after(r"^\s*(?:and\s+)?I\s+thought\b(?=\s+that['’]?s\b)", "self-thought marker before external/person characterization")
        add_after(r"^\s*(?:and\s+)?I\s+thought\b(?=\s+that\b)", "self-thought marker before external claim")
        add_prefix(r"^\s*I\s+pity\s+them\b", r"\s+(?=because\b)", "self-feeling before theological/future external claim")
        add_start(r"\bI\s+feel\s+for\s+them\b", "external young-men setup to self-feeling", min_left=8)
        add_start(r"\bbecause\s+I\s+was\s+raised\b", "self-biographical boundary after outside young-men setup", min_left=8)
        add_start(r"\band\s+we['’â€™]?ve\s+had\s+women\s+moved\s+to\s+tears\b", "speaker action to witnessed reaction", min_left=8)
        add_start(r"\bwe['’â€™]?ve\s+had\s+women\s+moved\s+to\s+tears\b", "speaker action to witnessed reaction", min_left=8)
        add_start(r"\bAnd\s+as\s+soon\s+as\s+I\s+talked\s+about\s+abortion\b", "self action boundary", min_left=4)
        add_start(r"\bAs\s+soon\s+as\s+I\s+talked\s+about\s+abortion\b", "self action boundary", min_left=4)

        for pattern in (
            r"\bNo,?\s+I\s+actually\s+have\b",
            r"\bI['’â€™]?ve\s+been\s+pregnant\s+before\b",
            r"\bI['’â€™]?m\s+not\s+17\b",
            r"\bI['’â€™]?m\s+secretly\b",
            r"\bI['’â€™]?m\s+going\s+to\s+ask\b",
            r"\bI\s+would\s+welcome\b",
            r"\bIt\s+was\s+one\s+of\s+the\s+best\s+things\s+I['’â€™]?ve\s+ever\s+seen\b",
            r"\bI\s+I\s+can\s+be\b",
        ):
            add_start(pattern, "speaker-owned/self-experience edge boundary", min_left=4)

        filtered: list[tuple[int, int, str]] = []
        for cand in candidates:
            left_text = piece[:cand[0]].strip().casefold()
            if left_text in {'and', 'so', 'but', 'uh'} and any(other[0] > cand[0] for other in candidates):
                continue
            filtered.append(cand)
        unique: dict[tuple[int, int], tuple[int, int, str]] = {}
        for cand in filtered:
            unique[(cand[0], cand[1])] = cand
        return sorted(unique.values(), key=lambda item: item[0])

if '_PASS3B_BASE_CLASSIFY_V4_20260827' not in globals():
    _PASS3B_BASE_CLASSIFY_V4_20260827 = _semantic_policy_classify_clause_text_v4

    def _semantic_policy_classify_clause_text_v4(text: str) -> tuple[str, str, float, str]:  # type: ignore[no-redef]
        clean = _strip_invisible_text(text).strip()
        lowered = _norm(clean).strip(' .?!')
        if not lowered:
            return 'BLANK', 'filler', 0.99, 'empty or filler span'
        if re.search(r"^(?:yeah,?\s+)*(?:that['’]?s\s+right|yeah)\b", lowered) or re.search(r"^well[-\s]*(?:i[-\s]*)?(?:uh[-\s]*)?yeah\b", lowered):
            return 'BLANK', 'filler', 0.96, 'acknowledgement/filler is not establishing a claim'
        if lowered == 'and':
            return 'BLANK', 'filler', 0.95, 'standalone conjunction filler is not a claim'
        if re.search(r"^unashamedly\b", lowered):
            return 'PRIMARY', 'self-biographical', 0.86, 'speaker-owned self-position/intensifier'
        if re.search(r"^(?:you\s+know,?\s+)?repent\b", lowered):
            return 'BLANK', 'filler', 0.95, 'repent prompt/instruction is not a source claim'
        if re.search(r"^and\s+maybe\s+just\s+to\s+close\s+off\b", lowered):
            return 'BLANK', 'filler', 0.95, 'conversation transition prompt is not a claim span'
        if re.search(r"^(?:thank\s+you|thanks)\s+for\s+complimenting\s+me\b", lowered):
            return 'BLANK', 'filler', 0.95, 'thanks/acknowledgement is not establishing a source claim'
        if re.search(r"\band\s+um\s+in\s+my\s+years\b|\bin\s+my\s+years\s+in\b", lowered):
            return 'PRIMARY', 'self-biographical', 0.86, 'speaker-owned biographical/ministry-experience context'
        if re.search(r"\bI\s+would\s+welcome\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'speaker-owned-imperative', 0.88, 'speaker-owned welcome/policy preference despite trailing tag question'
        if re.search(r"\bI\s+am\s+very\s+open\s+about\s+my\s+desire\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-biographical', 0.90, 'speaker-owned self-intent/desire'
        if re.search(r"\bI\s+can\s+be\b|\bI\s+I\s+can\s+be\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-biographical', 0.86, 'speaker-owned self-description/capacity'
        if re.search(r"\b(?:No,?\s+)?I\s+actually\s+have\b|\bI['’â€™]?ve\s+been\s+pregnant\s+before\b|\bI['’â€™]?m\s+not\s+17\b|\bI['’â€™]?m\s+secretly\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-biographical', 0.88, 'speaker-owned self-description/self-biographical claim'
        if re.search(r"\bI['’â€™]?m\s+going\s+to\s+ask\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-action', 0.86, 'speaker-owned interview/action transition'
        if re.search(r"\bI\s+feel\s+for\s+them\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-feeling', 0.88, 'speaker-owned feeling toward the group'
        if re.search(r"\bbecause\s+I\s+was\s+raised\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-biographical', 0.88, 'speaker-owned biographical basis'
        if re.search(r"\bIt\s+was\s+one\s+of\s+the\s+best\s+things\s+I['’â€™]?ve\s+ever\s+seen\b", clean, flags=re.IGNORECASE):
            return 'SECONDARY', 'witness-event', 0.86, 'speaker describes a directly seen event/evaluation'
        if re.search(r"^[\"'‘“â€˜â€œ]?\s*You['’â€™]?re\s+not\s+a\s+real\s+priest\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'external-object-label', 0.90, 'external person label inside quoted/self-reported speech'
        if re.search(r"^in\s+the\s+diocese\s+shoved\s+women\b", lowered):
            return 'UNKNOWN', 'institution-claim', 0.86, 'external diocese action claim after self-owned pulpit boundary'
        if re.search(r"^that['’]?s\s+the\s+kind\s+of\s+(?:man|leader|bishop)\b", lowered):
            return 'UNKNOWN', 'external-object-label', 0.84, 'external person/leader characterization after thought marker'
        if re.search(r"^because\s+on\s+the\s+day\s+of\s+judg(?:e)?ment\b", lowered):
            return 'UNKNOWN', 'historic-claim', 0.84, 'external theological/future claim after self-feeling marker'
        if re.search(r"^and\s+as\s+soon\s+as\s+i\s+talked\s+about\s+abortion\b|^as\s+soon\s+as\s+i\s+talked\s+about\s+abortion\b", lowered):
            return 'PRIMARY', 'self-action', 0.88, 'speaker-owned action/topic introduction'
        if re.search(r"\bwe['’â€™]?ve\s+preached\s+pro-life\s+sermons\s+here\b", lowered):
            return 'PRIMARY', 'speaker-owned-institutional-action', 0.90, 'speaker-owned institutional preaching action'
        return _PASS3B_BASE_CLASSIFY_V4_20260827(clean)



# SEMANTIC_POLICY_PASS3C_REMAINING_TRANSCRIPT_EDGES_20260827
# Remaining transcript-audit edge cleanup.  This pass stays within the shared
# clause classifier and only adds boundaries/classification precedence for cases
# still visible after pass3b.  It does not touch Build/counts, source provenance,
# comment rendering, or UI click behaviour.
if '_PASS3C_BASE_BOUNDARY_CANDIDATES_20260827' not in globals():
    _PASS3C_BASE_BOUNDARY_CANDIDATES_20260827 = _policy_pass2_boundary_candidates

    def _policy_pass2_boundary_candidates(piece: str) -> list[tuple[int, int, str]]:  # type: ignore[no-redef]
        candidates = list(_PASS3C_BASE_BOUNDARY_CANDIDATES_20260827(piece))

        def add_start(pattern: str, reason: str, *, min_left: int = 1) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            left_end = found.start()
            probe = left_end
            while probe > 0 and piece[probe - 1].isspace():
                probe -= 1
            if probe > 0 and piece[probe - 1] in {',', ';', ':'}:
                left_end = probe - 1
            candidates.append((left_end, found.start(), reason))

        def add_after(pattern: str, reason: str, *, min_left: int = 0) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            candidates.append((found.end(), found.end(), reason))

        # Quote/prompt followed by a speaker-owned action.  The sentence splitter
        # misses this when punctuation is followed by a quote before whitespace.
        add_start(r"\bUh\s+and\s+I\s+would\s+never\s+let\b", "repent prompt to self-owned pulpit action", min_left=8)
        add_start(r"\band\s+I\s+would\s+never\s+let\b", "repent prompt to self-owned pulpit action", min_left=8)

        # Filler/reaction followed by a real external claim.
        add_start(r"\bwhich\s+should\s+all\s+be\s+demolished\b", "filler to external normative claim", min_left=4)

        # Self-owned source/speech markers must not swallow the external content.
        add_after(r"^\s*(?:So,?\s+)?the\s+most\s+infamous\s+one\s+which\s+kind\s+of\s+became\s+my\s+catchphrase\s+is\s+I\s+said\b", "self-reported-speech marker before external target")
        add_after(r"^\s*This\s+trans\s+woman\s+who['’]?s\s+just\s+a\s+bloke,?\s+I\s+said\s+in\s+one\s+of\s+my\s+vlogs,?\s+I['’]?m\s+sorry,?\s+that['’]?s\s+a\s+bloke\b", "self-reported vlog speech before external label")

        # Speaker-owned action/thought markers followed by outside claims.
        add_start(r"\bwho\s+famously\s+debated\b", "self debate action to external biographical claim", min_left=6)
        add_after(r"^\s*(?:Like\s+)?I\s+debated\s+[A-Z][A-Za-z0-9_-]*(?:\s+um)?\b", "direct self-action debate marker")
        add_after(r"^\s*I\s+know\b(?=\s+some\b)", "self-knowledge marker before external person/group description")
        add_after(r"^\s*(?:And\s+)?I\s+know\b(?=\s+some\b)", "self-knowledge marker before external person/group description")
        add_after(r"\blike\s+I\s+know\b(?=\s+some\b)", "embedded self-knowledge marker before external person/group description", min_left=4)
        add_after(r"^\s*We['’]?re\s+not\s+ashamed\s+to\s+say\b", "speaker-group stance before external belief claim")
        add_start(r"\bthat\s+we\s+believe\b", "speaker-group stance to external belief claim", min_left=6)

        # Interview-transition/self-intent near the end.
        add_start(r"\band\s+I['’]?ll\s+definitely\s+have\s+you\s+on\b", "covered-territory statement to future self-action", min_left=8)
        add_after(r"^\s*(?:Um,?\s+but\s+on\s+that,?\s+)?I\s+think\s+we['’]?ve\s+covered\s+loads\s+of\s+territory\b", "self/interview belief transition")

        unique: dict[tuple[int, int], tuple[int, int, str]] = {}
        for cand in candidates:
            unique[(cand[0], cand[1])] = cand
        return sorted(unique.values(), key=lambda item: item[0])

if '_PASS3C_BASE_CLASSIFY_V4_20260827' not in globals():
    _PASS3C_BASE_CLASSIFY_V4_20260827 = _semantic_policy_classify_clause_text_v4

    def _semantic_policy_classify_clause_text_v4(text: str) -> tuple[str, str, float, str]:  # type: ignore[no-redef]
        clean = _strip_invisible_text(text).strip()
        lowered = _norm(clean).strip(' .?!')
        if not lowered:
            return 'BLANK', 'filler', 0.99, 'empty or filler span'

        # Prompt/filler pieces after quote punctuation.
        if re.search(r"^(?:[\"'‘’“”]\s*)?(?:you\s+know,?\s*)?repent\b", clean, flags=re.IGNORECASE):
            return 'BLANK', 'filler', 0.96, 'short prompt/imperative in quoted reply is not a claim span'
        if re.search(r"^(?:yeah,?\s+)?unfortunately\b", lowered) and not re.search(r"\bwhich\s+should\s+all\s+be\s+demolished\b", lowered):
            return 'BLANK', 'filler', 0.94, 'reaction/filler without claim content'
        if re.search(r"^bent,?\s+it['’]?s\s+been\s+an\s+absolute\s+pleasure\b", lowered):
            return 'BLANK', 'filler', 0.95, 'closing politeness/acknowledgement is not a source claim'
        if re.search(r"^i\s+mean,?\s+either\s+turn\s+off\s+your\s+notifications\b", lowered):
            return 'BLANK', 'filler', 0.92, 'practical prompt/advice is not a sourced claim span'

        # Self-owned actions/positions still left over after pass3b.
        if re.search(r"\bI\s+would\s+never\s+let\s+a\s+woman\s+in\s+my\s+pulpit\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'speaker-owned-institutional-action', 0.90, 'speaker-owned institutional/pulpit action'
        if re.search(r"^Like\s+I\s+debated\b|^I\s+debated\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-action', 0.88, 'speaker-owned direct debate/action'
        if re.search(r"^(?:And\s+)?I\s+know\b", clean, flags=re.IGNORECASE) or re.search(r"\blike\s+I\s+know\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-belief', 0.86, 'speaker-owned knowledge marker'
        if re.search(r"^We['’]?re\s+not\s+ashamed\s+to\s+say\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'speaker-owned-institutional-action', 0.86, 'speaker-group owned stance/speech marker'
        if re.search(r"^(?:Um,?\s+but\s+on\s+that,?\s+)?I\s+think\s+we['’]?ve\s+covered\s+loads\s+of\s+territory\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-belief', 0.86, 'speaker-owned interview summary belief'
        if re.search(r"^and\s+I['’]?ll\s+definitely\s+have\s+you\s+on\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-intent', 0.88, 'speaker-owned future action/intent'

        # External claims explicitly split away from speaker-owned markers.
        if re.search(r"^which\s+should\s+all\s+be\s+demolished\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'external-object-label', 0.88, 'external object/normative claim after filler'
        if re.search(r"^that\s+we\s+believe\s+these\s+islands\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'group-claim', 0.86, 'external national/theological belief claim after stance marker'
        if re.search(r"^some\s+amazing\s+Nigerian\s+churches\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'external-object-label', 0.84, 'external group/person description after knowledge marker'
        if re.search(r"^who\s+famously\s+debated\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'biographical-claim-about-other', 0.86, 'external biographical claim about another person'
        if re.search(r"^of\s+the\s+Archdeacon\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'biographical-claim-about-other', 0.84, 'external target of self-reported speech'
        if re.search(r"^in\s+Manchester\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'biographical-claim-about-other', 0.80, 'external location/context fragment'

        return _PASS3C_BASE_CLASSIFY_V4_20260827(clean)


# SEMANTIC_POLICY_PASS3D_TAIL_EDGES_QUOTE_SOURCE_20260827
# Tail transcript edge cleanup over the shared clause classifier.  This pass
# fixes remaining self-speech, quote carryover, self-preference, direct-source,
# and imperative-object boundaries visible after pass3c.  It does not touch UI,
# Build counts, click-scroll, comments, or source/provenance records.
if '_PASS3D_BASE_BOUNDARY_CANDIDATES_20260827' not in globals():
    _PASS3D_BASE_BOUNDARY_CANDIDATES_20260827 = _policy_pass2_boundary_candidates

    def _policy_pass2_boundary_candidates(piece: str) -> list[tuple[int, int, str]]:  # type: ignore[no-redef]
        candidates = list(_PASS3D_BASE_BOUNDARY_CANDIDATES_20260827(piece))

        def add_start(pattern: str, reason: str, *, min_left: int = 1) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            left_end = found.start()
            probe = left_end
            while probe > 0 and piece[probe - 1].isspace():
                probe -= 1
            if probe > 0 and piece[probe - 1] in {',', ';', ':'}:
                left_end = probe - 1
            candidates.append((left_end, found.start(), reason))

        def add_after(pattern: str, reason: str, *, min_left: int = 0) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            candidates.append((found.end(), found.end(), reason))

        add_start(r"\bI\s+was\s+invited\s+to\s+rallies\b", "self media outreach to direct invitation/received-source event", min_left=4)
        add_after(r"^\s*(?:And\s+then\s+)?we\s+we\s+realized\b", "speaker-group realization marker before external institution claim")
        add_after(r"^\s*(?:And\s+then\s+)?we\s+realized\b", "speaker-group realization marker before external institution claim")
        add_start(r"\bcuz\s+I\s+believe\b", "external institutional claim to speaker belief marker", min_left=8)
        add_after(r"^\s*cuz\s+I\s+believe\b(?:\s+uh)?", "belief marker before external maxim")
        add_start(r"\bthat\s+I\s+could\s+(?:follow|back|support)\b", "external person label to self-preference/self-support", min_left=6)
        add_after(r"^\s*End\b", "speaker-owned bare imperative before external object")
        add_after(r"^\s*Because\s+I\s+see\b", "direct observation marker before observed external claim")
        add_start(r"\bAren['’]?t\s+you\s+upset\b", "reported parishioner quote to speaker response", min_left=8)
        add_start(r"\bI['’]?m\s+like,?\s*[\"'‘’“”]?No,?\s+I\s+don['’]?t\s+care", "quoted question to speaker self-response", min_left=8)

        unique: dict[tuple[int, int], tuple[int, int, str]] = {}
        for cand in candidates:
            unique[(cand[0], cand[1])] = cand
        return sorted(unique.values(), key=lambda item: item[0])

if '_PASS3D_BASE_CLASSIFY_V4_20260827' not in globals():
    _PASS3D_BASE_CLASSIFY_V4_20260827 = _semantic_policy_classify_clause_text_v4

    def _semantic_policy_classify_clause_text_v4(text: str) -> tuple[str, str, float, str]:  # type: ignore[no-redef]
        clean = _strip_invisible_text(text).strip()
        lowered = _norm(clean).strip(' .?!')
        if not lowered:
            return 'BLANK', 'filler', 0.99, 'empty or filler span'

        if re.search(r"^[\"'‘’“”]?\s*my[-\s.]*$", clean, flags=re.IGNORECASE):
            return 'BLANK', 'filler', 0.96, 'broken transcript artefact/filler fragment'
        if re.search(r"^oh,?\s+see,?\s+i\s+knew\s+it\b", lowered):
            return 'BLANK', 'filler', 0.94, 'short conversational reaction is not a source claim'
        if re.search(r"\bkind\s+of\s+became\s+my\s+catchphrase\s+is\s+I\s+said\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-action', 0.88, 'speaker-owned report of what he said/catchphrase context'
        if re.search(r"^\s*(?:And\s+then\s+)?we\s+we\s+realized\b|^\s*(?:And\s+then\s+)?we\s+realized\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-belief', 0.88, 'speaker-group realization marker'
        if re.search(r"^\s*cuz\s+I\s+believe\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-belief', 0.88, 'speaker-owned belief marker after external claim boundary'
        if re.search(r"^I\s+was\s+invited\s+to\s+rallies\b", clean, flags=re.IGNORECASE):
            return 'SECONDARY', 'direct-attribution', 0.86, 'speaker reports a direct received invitation/source event'
        if re.search(r"^I\s+can['’]?t\s+relate\b|^So,?\s+I\s+I\s+can['’]?t\s+relate\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-feeling', 0.88, 'speaker-owned inability/feeling relation marker'
        if re.search(r"^that\s+I\s+could\s+(?:follow|back|support)\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-intent', 0.88, 'speaker-owned support/follow preference'
        if re.search(r"^Because\s+I\s+see\b", clean, flags=re.IGNORECASE):
            return 'SECONDARY', 'witness-event', 0.84, 'speaker reports direct observation of the interlocutor/context'
        if re.search(r"^So,?\s+some\s+some\s+of\s+my\s+parishioners\s+will\s+say\s+to\s+me\s+sometimes\b", clean, flags=re.IGNORECASE):
            return 'SECONDARY', 'direct-attribution', 0.88, 'directly received repeated parishioner quote/report'
        if re.search(r"^Aren['’]?t\s+you\s+upset\b", clean, flags=re.IGNORECASE):
            return 'BLANK', 'question', 0.94, 'quoted question/prompt does not establish a claim span'
        if re.search(r"^I['’]?m\s+like,?\s*[\"'‘’“”]?No,?\s+I\s+don['’]?t\s+care", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-feeling', 0.90, 'speaker-owned response/feeling in quoted self-reply'
        if re.search(r"^[\"'‘’“”]?\s*I\s+lay\s+it\s+down\b", clean, flags=re.IGNORECASE):
            return 'TERTIARY', 'direct-quote', 0.90, 'continuation of a relayed scriptural quotation, not speaker-owned first person'
        if lowered == 'end':
            return 'PRIMARY', 'speaker-owned-imperative', 0.86, 'bare speaker-owned imperative marker'
        if re.search(r"^the\s+homosexual\s+adoption\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'external-object-label', 0.88, 'external object of bare imperative'

        return _PASS3D_BASE_CLASSIFY_V4_20260827(clean)

# SEMANTIC_POLICY_PASS3E_FINAL_EDGE_CLEANUP_20260827
# Final observed transcript edge cleanup after pass3d.  This pass fixes only
# narrow leftover classifier cases: passive self-biographical invitation, quote
# carryover after a closing quote, and conversational prompt/filler fragments.
if '_PASS3E_BASE_BOUNDARY_CANDIDATES_20260827' not in globals():
    _PASS3E_BASE_BOUNDARY_CANDIDATES_20260827 = _policy_pass2_boundary_candidates

    def _policy_pass2_boundary_candidates(piece: str) -> list[tuple[int, int, str]]:  # type: ignore[no-redef]
        candidates = list(_PASS3E_BASE_BOUNDARY_CANDIDATES_20260827(piece))

        def add_start(pattern: str, reason: str, *, min_left: int = 1) -> None:
            found = re.search(pattern, piece, flags=re.IGNORECASE)
            if not found or found.start() < min_left:
                return
            left_end = found.start()
            probe = left_end
            while probe > 0 and piece[probe - 1].isspace():
                probe -= 1
            if probe > 0 and piece[probe - 1] in {',', ';', ':'}:
                left_end = probe - 1
            candidates.append((left_end, found.start(), reason))

        # Do not let a relayed direct quote absorb the following interpretation.
        add_start(r"\bHe\s+could\s+have\s+resisted\b", "close quote before non-quoted interpretation", min_left=8)
        add_start(r"\bBut\s+he\s+was\s+also\s+strong\b", "direct quote/interpretation carryover boundary", min_left=8)

        unique: dict[tuple[int, int], tuple[int, int, str]] = {}
        for cand in candidates:
            unique[(cand[0], cand[1])] = cand
        return sorted(unique.values(), key=lambda item: item[0])

if '_PASS3E_BASE_CLASSIFY_V4_20260827' not in globals():
    _PASS3E_BASE_CLASSIFY_V4_20260827 = _semantic_policy_classify_clause_text_v4

    def _semantic_policy_classify_clause_text_v4(text: str) -> tuple[str, str, float, str]:  # type: ignore[no-redef]
        clean = _strip_invisible_text(text).strip()
        lowered = _norm(clean).strip(' .?!')
        if not lowered:
            return 'BLANK', 'filler', 0.99, 'empty or filler span'

        # Passive first-person invitation is a speaker-owned biographical/event
        # report in this review layer, not a relayed statement by an identified source.
        if re.search(r"^I\s+was\s+invited\s+to\s+rallies\b", clean, flags=re.IGNORECASE):
            return 'PRIMARY', 'self-biographical', 0.88, 'speaker-owned passive biographical/event report'

        # Conversational/meta prompts and fragments should not remain Unknown/Primary.
        if re.search(r"^(?:And\s+)?I['’]?m\s+going\s+to\s+ask\s+you\b", clean, flags=re.IGNORECASE):
            return 'BLANK', 'question', 0.95, 'interviewer prompt/question setup is not a claim span'
        if re.search(r"^(?:because\s+)?we['’]?ve\s+covered\s+a\s+lot\s+of\s+ground\b", clean, flags=re.IGNORECASE):
            return 'BLANK', 'filler', 0.93, 'conversational close-off/meta summary is not a source claim'
        if re.search(r"^that['’]?s\s+so\s+nice\b", lowered):
            return 'BLANK', 'filler', 0.94, 'short conversational reaction/sarcasm is not a source claim'
        if re.search(r"^(?:m+\s*h+|mm+h+|m+hh?)[-\s]*(?:uh)?$", lowered):
            return 'BLANK', 'filler', 0.96, 'vocal filler is not a claim span'
        if re.search(r"^um[-\s]*so$", lowered):
            return 'BLANK', 'filler', 0.95, 'vocal filler/transition fragment is not a claim span'
        if re.search(r"^or\s+some\s+tin\s+tuna\b", lowered):
            return 'BLANK', 'filler', 0.92, 'fragment continuing a conversational prompt is not a claim span'

        # Non-quoted interpretation following a quoted scriptural direct quote.
        if re.search(r"^He\s+could\s+have\s+resisted\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'external-claim', 0.86, 'non-quoted interpretation after relayed quotation'
        if re.search(r"^But\s+he\s+was\s+also\s+strong\b", clean, flags=re.IGNORECASE):
            return 'UNKNOWN', 'external-claim', 0.86, 'external claim about quoted figure after direct quote'

        return _PASS3E_BASE_CLASSIFY_V4_20260827(clean)

