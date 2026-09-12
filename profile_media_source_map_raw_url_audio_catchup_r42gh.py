from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_universal_source_map_r42gg import (
    R42GG_PASS_STATUS,
    SIDE_EFFECT_BOUNDARY,
    SOURCE_FAMILY_BY_ID,
    STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_SOURCE_ROUTE_WORKS,
    build_capture_plan,
    detect_source_family,
    sanitize_source_input,
    sanitize_source_url,
    validate_universal_source_map,
)

R42GH_MARKER = "YTCE_R42GH_SOURCE_MAP_RAW_URL_AUDIO_CATCHUP_REPAIR"
R42GH_PASS_STATUS = "PASS_R42GH_SOURCE_MAP_RAW_URL_AUDIO_CATCHUP_REPAIR"
R42GH_BLOCKED_STATUS = "BLOCKED_R42GH_WITH_EXACT_BLOCKER"
R42GH_SCHEMA_VERSION = "source_map_raw_url_audio_catchup.r42gh.v1"

GLOBAL_PLAYER_LBC_FIXTURE_URL = "https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/"

GLOBAL_PLAYER_METHOD_METADATA: Mapping[str, object] = {
    "backend_id": "yt_dlp_python_module",
    "preferred_invocation": "py -m yt_dlp",
    "avoid_plain_executable_when_path_stale": True,
    "format_probe_required": True,
    "format_probe_command_shape": "py -m yt_dlp -vU -F <url>",
    "native_format_id_observed": "0",
    "native_container": "m4a",
    "preserve_native_container": True,
    "preserve_native_m4a": True,
    "write_info_json": True,
    "write_description": True,
    "write_thumbnail": True,
    "no_conversion_for_preservation": True,
    "observed_bad_path_executable_error": '[GlobalPlayerAudioEpisode] Missing "id" field in extractor result',
    "observed_working_nightly_version": "2026.08.30.232658",
}


@dataclass(frozen=True)
class AudioCatchupEvidenceRecord:
    platform_or_provider: str
    station_or_publisher: str
    programme_or_show: str
    episode_title: str
    episode_id: str
    source_url: str
    canonical_url: str
    capture_time_iso: str
    capture_timezone: str
    backend_id: str
    backend_version: str
    preferred_invocation: str
    format_id: str
    native_container: str
    media_relative_path: str
    sidecar_paths: tuple[str, ...]
    preservation_policy: str
    raw_url: str = ""
    source_fingerprint: str = ""

    def with_fingerprint(self) -> "AudioCatchupEvidenceRecord":
        if self.source_fingerprint:
            return self
        payload = "|".join(
            [
                self.platform_or_provider,
                self.station_or_publisher,
                self.programme_or_show,
                self.episode_id,
                self.canonical_url,
                self.media_relative_path,
                ",".join(self.sidecar_paths),
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:24]
        data = asdict(self)
        data["source_fingerprint"] = f"sha256:{digest}"
        return AudioCatchupEvidenceRecord(**data)

    def to_dict(self) -> dict[str, Any]:
        record = self.with_fingerprint()
        data = asdict(record)
        data["sidecar_paths"] = list(record.sidecar_paths)
        data["review_strings"] = build_audio_catchup_review_strings(record)
        return data


@dataclass(frozen=True)
class R42GHReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    checks: tuple[Mapping[str, str], ...]
    sample_plans: tuple[Mapping[str, Any], ...]
    audio_evidence_shape: Mapping[str, Any]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GH_PASS_STATUS and all(check.get("status") != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_evidence_shape": dict(self.audio_evidence_shape),
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "passed": self.passed,
            "sample_plans": [dict(plan) for plan in self.sample_plans],
            "schema_version": self.schema_version,
            "side_effect_boundary": self.side_effect_boundary,
            "source_root": self.source_root,
            "status": self.status,
        }


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def is_plain_machine_url(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text) and not text.startswith("[") and "](" not in text


def sample_url_inputs() -> tuple[str, ...]:
    return (
        "https://x.com/examaddaorg?utm_source=test&s=20",
        "[https://x.com/examaddaorg?utm_source=test&s=20](https://x.com/examaddaorg?utm_source=test&s=20)",
        "[Example](https://x.com/BBCr4today/status/2097217541416308845?s=20)",
        r"https:\/\/x.com\/BBCr4today\/status\/2097217541416308845?s=20",
        "https://twitter.com/BBCr4today/status/2097217541416308845?s=20",
        "[Metro](https://metro.co.uk/example/?utm_campaign=x)",
        GLOBAL_PLAYER_LBC_FIXTURE_URL,
    )


def build_audio_catchup_export_layout(station_or_publisher: str, capture_timestamp: str) -> Mapping[str, Any]:
    station = re.sub(r"[^a-zA-Z0-9_.-]+", "_", station_or_publisher).strip("_") or "station"
    stamp = re.sub(r"[^0-9TtZz_.-]+", "_", capture_timestamp).strip("_") or "capture"
    root = f"source_exports/public_broadcast_catchup_audio/{station}/capture_{stamp}"
    return {
        "root": root,
        "manifest": f"{root}/manifest.json",
        "episode_markdown": f"{root}/episode.md",
        "episode_json": f"{root}/episode.json",
        "media_original": f"{root}/media/original.m4a",
        "sidecars": {
            "info_json": f"{root}/sidecars/info.json",
            "description": f"{root}/sidecars/description.txt",
            "thumbnail_glob": f"{root}/sidecars/thumbnail.*",
        },
        "review_strings": f"{root}/review_strings.txt",
    }


def build_lbc_global_player_evidence_record(
    *,
    capture_time_iso: str = "2026-09-12T00:00:00Z",
    backend_version: str = "2026.08.30.232658",
) -> AudioCatchupEvidenceRecord:
    canonical = sanitize_source_url(GLOBAL_PLAYER_LBC_FIXTURE_URL)
    return AudioCatchupEvidenceRecord(
        platform_or_provider="Global Player",
        station_or_publisher="lbc",
        programme_or_show="Nick Ferrari",
        episode_title="Nick Ferrari",
        episode_id="2zGwFmzE7xNLAfiMVL5BMHmPeB",
        source_url=canonical,
        canonical_url=canonical,
        raw_url=GLOBAL_PLAYER_LBC_FIXTURE_URL,
        capture_time_iso=capture_time_iso,
        capture_timezone="UTC",
        backend_id=str(GLOBAL_PLAYER_METHOD_METADATA["backend_id"]),
        backend_version=backend_version,
        preferred_invocation=str(GLOBAL_PLAYER_METHOD_METADATA["preferred_invocation"]),
        format_id=str(GLOBAL_PLAYER_METHOD_METADATA["native_format_id_observed"]),
        native_container=str(GLOBAL_PLAYER_METHOD_METADATA["native_container"]),
        media_relative_path="media/original.m4a",
        sidecar_paths=("sidecars/info.json", "sidecars/description.txt", "sidecars/thumbnail.jpg"),
        preservation_policy="preserve_native_m4a_no_conversion",
    ).with_fingerprint()


def build_audio_catchup_review_strings(record: AudioCatchupEvidenceRecord) -> tuple[str, ...]:
    record = record.with_fingerprint()
    media_name = Path(record.media_relative_path).name
    values = [
        record.canonical_url,
        record.raw_url,
        record.episode_id,
        record.programme_or_show,
        record.station_or_publisher,
        record.episode_title,
        media_name,
        record.media_relative_path,
        *record.sidecar_paths,
        record.source_fingerprint,
    ]
    return tuple(_dedupe(value for value in values if value))


def build_audio_catchup_plan(url: str = GLOBAL_PLAYER_LBC_FIXTURE_URL) -> Mapping[str, Any]:
    plan = build_capture_plan(url)
    family = SOURCE_FAMILY_BY_ID["public_broadcast_catchup_audio"]
    return {
        "capture_plan": plan.to_dict(),
        "method_metadata": dict(family.method_metadata or GLOBAL_PLAYER_METHOD_METADATA),
        "audio_export_layout": dict(build_audio_catchup_export_layout("lbc", "20260912T000000Z")),
    }


def _dedupe(values: Any) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _sample_plan_url_check(sample_plans: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    failures: list[str] = []
    for plan in sample_plans:
        sanitized = plan["sanitized_input"]
        for field in ("extracted_url", "normalized_url"):
            value = str(sanitized.get(field, ""))
            if not is_plain_machine_url(value):
                failures.append(f"{field}={value}")
    return (not failures, "; ".join(failures))


def validate_source_map_raw_url_audio_catchup(source_root: str | Path = ".") -> R42GHReport:
    sample_plans = tuple(build_capture_plan(value).to_dict() for value in sample_url_inputs())
    plain_ok, plain_detail = _sample_plan_url_check(sample_plans)
    family = SOURCE_FAMILY_BY_ID.get("public_broadcast_catchup_audio")
    global_plan = build_audio_catchup_plan()
    evidence = build_lbc_global_player_evidence_record()
    evidence_dict = evidence.to_dict()
    review_strings = build_audio_catchup_review_strings(evidence)
    gg_report = validate_universal_source_map(source_root)
    checks = (
        _check("sample_plan_urls_are_plain_not_markdown", plain_ok, plain_detail),
        _check("r42gg_still_green", gg_report.status == R42GG_PASS_STATUS, gg_report.status),
        _check("global_player_family_detected", detect_source_family(GLOBAL_PLAYER_LBC_FIXTURE_URL) == "public_broadcast_catchup_audio"),
        _check("global_player_family_registered", family is not None and "lbc_global_player" in family.platform_aliases),
        _check("global_player_method_metadata", global_plan["method_metadata"].get("backend_id") == "yt_dlp_python_module" and global_plan["method_metadata"].get("preferred_invocation") == "py -m yt_dlp"),
        _check("native_m4a_preservation_policy", evidence.native_container == "m4a" and evidence.preservation_policy == "preserve_native_m4a_no_conversion"),
        _check("audio_sidecars_represented", {"sidecars/info.json", "sidecars/description.txt", "sidecars/thumbnail.jpg"}.issubset(set(evidence.sidecar_paths))),
        _check("audio_review_strings_bridge", all(item in review_strings for item in (evidence.canonical_url, evidence.episode_id, "original.m4a", "sidecars/info.json", evidence.source_fingerprint))),
        _check("source_role_guardrail", "no source-role" in SIDE_EFFECT_BOUNDARY and "no media download" in SIDE_EFFECT_BOUNDARY),
    )
    status = R42GH_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GH_BLOCKED_STATUS
    return R42GHReport(
        marker=R42GH_MARKER,
        schema_version=R42GH_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(Path(source_root)),
        status=status,
        checks=checks,
        sample_plans=sample_plans,
        audio_evidence_shape=evidence_dict,
    )


def _write_report(output_root: Path, report: R42GHReport) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "R42GH_SOURCE_MAP_AUDIO_CATCHUP_REPORT.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_root / "R42GH_AUDIO_CATCHUP_EVIDENCE_SCHEMA.json").write_text(
        json.dumps(build_audio_catchup_plan(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        f"# {R42GH_MARKER}",
        "",
        f"Status: {report.status}",
        f"Generated: {report.generated_at}",
        "",
        "## Checks",
    ]
    lines.extend(f"- {check['status'].upper()} {check['name']}: {check.get('detail', '')}" for check in report.checks)
    lines.extend(
        [
            "",
            "## Side Effect Boundary",
            SIDE_EFFECT_BOUNDARY,
            "",
            "## Public Audio/Catch-up Method",
            json.dumps(dict(GLOBAL_PLAYER_METHOD_METADATA), indent=2, sort_keys=True),
        ]
    )
    (output_root / "R42GH_SOURCE_MAP_AUDIO_CATCHUP_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R42GH_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gh_source_map_audio_catchup")
    args = parser.parse_args(argv)
    report = validate_source_map_raw_url_audio_catchup(args.source_root)
    _write_report(Path(args.output_root), report)
    print(R42GH_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


__all__ = [
    "AudioCatchupEvidenceRecord",
    "GLOBAL_PLAYER_LBC_FIXTURE_URL",
    "GLOBAL_PLAYER_METHOD_METADATA",
    "R42GH_BLOCKED_STATUS",
    "R42GH_MARKER",
    "R42GH_PASS_STATUS",
    "R42GHReport",
    "build_audio_catchup_export_layout",
    "build_audio_catchup_plan",
    "build_audio_catchup_review_strings",
    "build_lbc_global_player_evidence_record",
    "is_plain_machine_url",
    "sample_url_inputs",
    "validate_source_map_raw_url_audio_catchup",
]


if __name__ == "__main__":
    raise SystemExit(main())
