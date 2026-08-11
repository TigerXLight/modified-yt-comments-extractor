from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit
import zlib


PYWB_INDEXABLE_NAME = "rendered-page.pywb-indexable.warc.gz"
REPLAY_STATUS_JSON = "archive_replay_status.json"
REPLAY_STATUS_TXT = "archive_replay_status.txt"
RECOMPRESS_REPORT_JSON = "warc_pywb_recompression_report.json"
RECOMPRESS_REPORT_TXT = "warc_pywb_recompression_report.txt"


@dataclass
class FileReceipt:
    path: str
    exists: bool
    size: int = 0
    sha256: str = ""


@dataclass
class RecompressionReport:
    input_path: str
    output_path: str
    input_exists: bool
    output_exists: bool
    raw_warc_size: int
    record_count: int
    gzip_member_count: int
    output_sha256: str
    status: str
    warnings: list[str]
    errors: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_closeout_url(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().strip('"').strip("'")
    if text.startswith("[") and "](" in text and text.endswith(")"):
        text = text[text.find("](") + 2 : -1]
    text = text.replace("^&", "&")
    text = text.replace("\\&", "&")
    text = text.replace("%5E%26", "%26").replace("%5e%26", "%26")
    return text


def without_fragment(value: Any) -> str:
    url = normalize_closeout_url(value)
    if not url:
        return ""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def file_receipt(path: Path | None) -> FileReceipt:
    if path is None:
        return FileReceipt(path="", exists=False)
    if not path.exists():
        return FileReceipt(path=str(path), exists=False)
    return FileReceipt(path=str(path), exists=True, size=path.stat().st_size, sha256=sha256_file(path))


def read_warc_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() == ".gz" or data.startswith(b"\x1f\x8b"):
        with gzip.open(path, "rb") as f:
            return f.read()
    return data


def _find_header_end(raw: bytes, start: int) -> tuple[int, int]:
    crlf = raw.find(b"\r\n\r\n", start)
    lf = raw.find(b"\n\n", start)
    candidates = [(crlf, 4), (lf, 2)]
    candidates = [(idx, size) for idx, size in candidates if idx >= 0]
    if not candidates:
        return -1, 0
    return min(candidates, key=lambda item: item[0])


def iter_warc_records(raw: bytes) -> Iterable[bytes]:
    """Yield raw WARC records from a decompressed WARC byte stream.

    The existing adapter had produced a valid WARC inside a single gzip stream.
    pywb/warcio expects each WARC record to be separately gzipped.  This splitter
    uses WARC Content-Length boundaries and then the recompressor writes one gzip
    member per record.
    """
    pos = 0
    n = len(raw)
    while pos < n:
        while pos < n and raw[pos : pos + 1] in (b"\r", b"\n", b" ", b"\t", b"\x00"):
            pos += 1
        start = raw.find(b"WARC/1.", pos)
        if start < 0:
            break
        header_end, sep_len = _find_header_end(raw, start)
        if header_end < 0:
            break
        header_blob = raw[start:header_end]
        try:
            header_text = header_blob.decode("iso-8859-1")
        except UnicodeDecodeError:
            header_text = header_blob.decode("utf-8", errors="replace")
        content_length = None
        for line in header_text.splitlines():
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    content_length = None
                break
        if content_length is None:
            break
        body_start = header_end + sep_len
        body_end = body_start + content_length
        if body_end > n:
            break
        record_end = body_end
        appended_terminator = False
        if raw.startswith(b"\r\n\r\n", record_end):
            record_end += 4
        elif raw.startswith(b"\n\n", record_end):
            record_end += 2
        else:
            appended_terminator = True
        record = raw[start:record_end]
        if appended_terminator:
            record += b"\r\n\r\n"
        yield record
        pos = record_end


def count_gzip_members(path: Path) -> int:
    data = path.read_bytes()
    count = 0
    remaining = data
    while remaining:
        dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            dec.decompress(remaining)
        except zlib.error:
            break
        if not dec.eof:
            break
        count += 1
        remaining = dec.unused_data
        if not remaining:
            break
    return count


def recompress_warc_for_pywb(input_path: Path, output_path: Path) -> RecompressionReport:
    warnings: list[str] = []
    errors: list[str] = []
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        return RecompressionReport(
            input_path=str(input_path),
            output_path=str(output_path),
            input_exists=False,
            output_exists=False,
            raw_warc_size=0,
            record_count=0,
            gzip_member_count=0,
            output_sha256="",
            status="INPUT_WARC_NOT_FOUND",
            warnings=warnings,
            errors=[f"input not found: {input_path}"],
        )
    try:
        raw = read_warc_bytes(input_path)
        records = list(iter_warc_records(raw))
        if not records:
            errors.append("no WARC records could be parsed from input")
            return RecompressionReport(str(input_path), str(output_path), True, False, len(raw), 0, 0, "", "NO_WARC_RECORDS_PARSED", warnings, errors)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as out:
            for record in records:
                out.write(gzip.compress(record, compresslevel=6))
        members = count_gzip_members(output_path)
        digest = sha256_file(output_path)
        if members != len(records):
            warnings.append(f"gzip_member_count {members} differs from record_count {len(records)}")
        status = "PYWB_INDEXABLE_WARC_GZ_GENERATED" if members >= len(records) else "PYWB_INDEXABLE_WARC_GZ_REVIEW_REQUIRED"
        return RecompressionReport(str(input_path), str(output_path), True, output_path.exists(), len(raw), len(records), members, digest, status, warnings, errors)
    except Exception as exc:
        errors.append(type(exc).__name__ + ": " + str(exc))
        return RecompressionReport(str(input_path), str(output_path), True, output_path.exists(), 0, 0, 0, "", "RECOMPRESSION_FAILED", warnings, errors)


def inspect_wacz(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": "", "exists": False, "status": "WACZ_NOT_FOUND"}
    info: dict[str, Any] = asdict(file_receipt(path))
    if not path.exists():
        info["status"] = "WACZ_NOT_FOUND"
        return info
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            info["zip_readable"] = True
            info["entry_count"] = len(names)
            info["has_datapackage_json"] = "datapackage.json" in names
            info["has_pages"] = any(n.startswith("pages/") for n in names)
            info["has_indexes"] = any(n.startswith("indexes/") for n in names)
            info["has_archive"] = any(n.startswith("archive/") for n in names)
            info["sample_entries"] = names[:20]
            profile = ""
            if "datapackage.json" in names:
                try:
                    dp = json.loads(zf.read("datapackage.json").decode("utf-8", errors="replace"))
                    profile = str(dp.get("profile", ""))
                    info["datapackage_profile"] = profile
                    info["datapackage_name"] = dp.get("name", "")
                    info["datapackage_version"] = dp.get("version", "")
                except Exception as exc:
                    info["datapackage_error"] = type(exc).__name__ + ": " + str(exc)
            if profile.lower() == "wacz":
                info["status"] = "GENERATED_COMPATIBILITY_REVIEW_REQUIRED_PROFILE_WACZ"
                info["note"] = "Prior manual ReplayWeb test on this WACZ profile family failed with Unknown package profile: wacz; regenerate/verify before marking compatible."
            else:
                info["status"] = "GENERATED_COMPATIBILITY_NOT_VISUALLY_TESTED"
    except zipfile.BadZipFile:
        info["zip_readable"] = False
        info["status"] = "WACZ_BAD_ZIP"
    except Exception as exc:
        info["zip_readable"] = False
        info["status"] = "WACZ_INSPECTION_ERROR"
        info["error"] = type(exc).__name__ + ": " + str(exc)
    return info


def _result_get(result: Any, names: Iterable[str]) -> Any:
    if result is None:
        return None
    for name in names:
        if isinstance(result, dict):
            for key in (name, name.upper(), name.lower()):
                if key in result and result.get(key):
                    return result.get(key)
        if hasattr(result, name):
            value = getattr(result, name)
            if value:
                return value
    return None


def _coerce_path(value: Any) -> Path | None:
    if not value:
        return None
    try:
        return Path(str(value))
    except Exception:
        return None


def resolve_output_root(result: Any = None, args: tuple[Any, ...] = (), kwargs: dict[str, Any] | None = None) -> Path:
    kwargs = kwargs or {}
    for value in (
        kwargs.get("output_dir"), kwargs.get("output_root"), kwargs.get("root"),
        _result_get(result, ("output_dir", "output_root", "root")),
    ):
        p = _coerce_path(value)
        if p:
            return p
    for name in ("html_export", "json_export", "comments_html", "comments_json", "rendered_page_html"):
        p = _coerce_path(_result_get(result, (name,)))
        if p:
            return p.parent if p.suffix else p
    for item in args:
        p = _coerce_path(item)
        if p and (p.exists() or "msn_" in str(p).lower()):
            return p
    raise RuntimeError("replay hardening could not resolve output_root")


def normalize_result_urls(result: Any) -> None:
    if not isinstance(result, dict):
        return
    for key in ("ARTICLE_URL", "article_url", "COMMENTS_URL", "comments_url", "TARGET_URL", "target_url"):
        if key in result and result.get(key):
            value = normalize_closeout_url(result[key])
            if key.upper().startswith("ARTICLE") or key.upper().startswith("TARGET"):
                value = without_fragment(value)
            result[key] = value


def find_first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def build_replay_status(output_root: Path, recompress: RecompressionReport) -> dict[str, Any]:
    live = output_root / "live_capture"
    rendered_html = find_first_existing([live / "rendered-page.html", output_root / "rendered-page.html"])
    original_warc_gz = find_first_existing([live / "rendered-page.warc.gz", output_root / "rendered-page.warc.gz"])
    raw_warc = find_first_existing([live / "rendered-page.warc", output_root / "rendered-page.warc"])
    wacz = find_first_existing([live / "archive.viewable-live-capture.wacz", output_root / "archive.viewable-live-capture.wacz"])
    pywb_warc = Path(recompress.output_path) if recompress.output_path else live / PYWB_INDEXABLE_NAME

    markers = [
        "Arrest made after shot fired",
        "Tom Wilkinson",
        "The Independent",
        "AA292lx3",
        "York Mosque",
    ]
    html_marker_hits: dict[str, bool] = {}
    if rendered_html and rendered_html.exists():
        try:
            text = rendered_html.read_text(encoding="utf-8", errors="ignore")
            html_marker_hits = {m: (m in text) for m in markers}
        except Exception:
            html_marker_hits = {}

    wacz_info = inspect_wacz(wacz)
    pywb_structural_status = "PASS" if recompress.status == "PYWB_INDEXABLE_WARC_GZ_GENERATED" else "REVIEW_REQUIRED"
    report = {
        "generated_at_utc": utc_now_iso(),
        "output_root": str(output_root),
        "rendered_html": asdict(file_receipt(rendered_html)),
        "original_warc_gz": asdict(file_receipt(original_warc_gz)),
        "raw_warc": asdict(file_receipt(raw_warc)),
        "pywb_indexable_warc_gz": asdict(file_receipt(pywb_warc)),
        "wacz": wacz_info,
        "rendered_html_marker_hits": html_marker_hits,
        "warc_recompression": asdict(recompress),
        "warc_replay_status": "PYWB_INDEXABLE_SIDECAR_GENERATED_VISUAL_REPLAY_NOT_TESTED" if pywb_structural_status == "PASS" else "REVIEW_REQUIRED",
        "warc_replay_structural_status": pywb_structural_status,
        "replayweb_warc_visual_status": "MANUAL_TEST_REQUIRED; prior ReplayWeb article replay was PASS/PARTIAL for earlier WARC.GZ, but this closeout is not automatically visually tested.",
        "pywb_visual_replay_status": "NOT_ACCEPTED_PREVIOUS_PROBE_OR_NOT_TESTED_IN_THIS_CLOSEOUT",
        "wacz_replay_status": wacz_info.get("status", "WACZ_REVIEW_REQUIRED"),
        "wacz_visual_replay_status": "NOT_ACCEPTED_PREVIOUS_REPLAYWEB_UNKNOWN_PACKAGE_PROFILE_OR_NOT_TESTED_IN_THIS_CLOSEOUT",
        "limitations": [
            "This hardening makes a pywb-indexable WARC.GZ sidecar by writing one gzip member per WARC record.",
            "It does not claim automated browser visual replay success.",
            "WACZ remains compatibility-review-required unless separately verified in ReplayWeb or another WACZ viewer.",
            "Comments runtime replay inside WARC/WACZ is not required when comments are preserved by structured exports and accepted stitched screenshots.",
        ],
    }
    return report


def write_text_report(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("MSN ARCHIVE REPLAY HARDENING STATUS")
    lines.append(f"generated_at_utc: {report.get('generated_at_utc')}")
    lines.append(f"output_root: {report.get('output_root')}")
    lines.append("")
    lines.append(f"WARC_REPLAY_STATUS: {report.get('warc_replay_status')}")
    lines.append(f"WARC_REPLAY_STRUCTURAL_STATUS: {report.get('warc_replay_structural_status')}")
    lines.append(f"REPLAYWEB_WARC_VISUAL_STATUS: {report.get('replayweb_warc_visual_status')}")
    lines.append(f"PYWB_VISUAL_REPLAY_STATUS: {report.get('pywb_visual_replay_status')}")
    lines.append(f"WACZ_REPLAY_STATUS: {report.get('wacz_replay_status')}")
    lines.append(f"WACZ_VISUAL_REPLAY_STATUS: {report.get('wacz_visual_replay_status')}")
    lines.append("")
    lines.append("FILES:")
    for key in ("rendered_html", "original_warc_gz", "raw_warc", "pywb_indexable_warc_gz", "wacz"):
        item = report.get(key, {}) or {}
        lines.append(f"- {key}: exists={item.get('exists')} size={item.get('size', 0)} sha256={item.get('sha256', '')} path={item.get('path', '')}")
    lines.append("")
    rec = report.get("warc_recompression", {}) or {}
    lines.append("PYWB RECOMPRESSION:")
    lines.append(f"status: {rec.get('status')}")
    lines.append(f"record_count: {rec.get('record_count')}")
    lines.append(f"gzip_member_count: {rec.get('gzip_member_count')}")
    lines.append(f"output_sha256: {rec.get('output_sha256')}")
    lines.append(f"warnings: {'; '.join(rec.get('warnings') or []) or 'NONE'}")
    lines.append(f"errors: {'; '.join(rec.get('errors') or []) or 'NONE'}")
    lines.append("")
    lines.append("WACZ INSPECTION:")
    wacz = report.get("wacz", {}) or {}
    for field in ("status", "zip_readable", "entry_count", "datapackage_profile", "has_datapackage_json", "has_pages", "has_indexes", "has_archive", "note"):
        if field in wacz:
            lines.append(f"{field}: {wacz.get(field)}")
    lines.append("")
    lines.append("RENDERED HTML MARKER HITS:")
    for marker, hit in (report.get("rendered_html_marker_hits") or {}).items():
        lines.append(f"- {marker}: {hit}")
    lines.append("")
    lines.append("LIMITATIONS:")
    for item in report.get("limitations", []):
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_recompression_text(report: RecompressionReport, path: Path) -> None:
    lines = [
        "WARC.GZ PYWB RECOMPRESSION REPORT",
        f"input_path: {report.input_path}",
        f"output_path: {report.output_path}",
        f"input_exists: {report.input_exists}",
        f"output_exists: {report.output_exists}",
        f"raw_warc_size: {report.raw_warc_size}",
        f"record_count: {report.record_count}",
        f"gzip_member_count: {report.gzip_member_count}",
        f"output_sha256: {report.output_sha256}",
        f"status: {report.status}",
        f"warnings: {'; '.join(report.warnings) or 'NONE'}",
        f"errors: {'; '.join(report.errors) or 'NONE'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def integrate_replay_hardening_for_closeout(result: Any = None, args: tuple[Any, ...] = (), kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    kwargs = kwargs or {}
    output_root = resolve_output_root(result=result, args=args, kwargs=kwargs)
    output_root.mkdir(parents=True, exist_ok=True)
    normalize_result_urls(result)

    live = output_root / "live_capture"
    warc_input = find_first_existing([live / "rendered-page.warc", live / "rendered-page.warc.gz", output_root / "rendered-page.warc", output_root / "rendered-page.warc.gz"])
    pywb_output = live / PYWB_INDEXABLE_NAME if live.exists() else output_root / PYWB_INDEXABLE_NAME
    recompress = recompress_warc_for_pywb(warc_input or (live / "rendered-page.warc.gz"), pywb_output)

    replay_status = build_replay_status(output_root, recompress)
    replay_json = output_root / REPLAY_STATUS_JSON
    replay_txt = output_root / REPLAY_STATUS_TXT
    recompress_json = output_root / RECOMPRESS_REPORT_JSON
    recompress_txt = output_root / RECOMPRESS_REPORT_TXT
    replay_json.write_text(json.dumps(replay_status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_text_report(replay_status, replay_txt)
    recompress_json.write_text(json.dumps(asdict(recompress), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_recompression_text(recompress, recompress_txt)

    print(f"PYWB_INDEXABLE_WARC_GZ: {pywb_output if pywb_output.exists() else ''}")
    print(f"ARCHIVE_REPLAY_STATUS_JSON: {replay_json}")
    print(f"ARCHIVE_REPLAY_STATUS_TXT: {replay_txt}")
    print(f"WARC_PYWB_RECOMPRESSION_REPORT_JSON: {recompress_json}")
    print(f"WARC_PYWB_RECOMPRESSION_REPORT_TXT: {recompress_txt}")

    if isinstance(result, dict):
        result["PYWB_INDEXABLE_WARC_GZ"] = str(pywb_output)
        result["PYWB_INDEXABLE_WARC_GZ_GENERATED"] = bool(pywb_output.exists())
        result["PYWB_INDEXABLE_WARC_GZ_RECORD_COUNT"] = recompress.record_count
        result["PYWB_INDEXABLE_WARC_GZ_GZIP_MEMBER_COUNT"] = recompress.gzip_member_count
        result["ARCHIVE_REPLAY_STATUS_JSON"] = str(replay_json)
        result["ARCHIVE_REPLAY_STATUS_TXT"] = str(replay_txt)
        result["WARC_PYWB_RECOMPRESSION_REPORT_JSON"] = str(recompress_json)
        result["WARC_PYWB_RECOMPRESSION_REPORT_TXT"] = str(recompress_txt)
        result["WARC_REPLAY_STATUS"] = replay_status["warc_replay_status"]
        result["WARC_REPLAY_STRUCTURAL_STATUS"] = replay_status["warc_replay_structural_status"]
        result["PYWB_VISUAL_REPLAY_STATUS"] = replay_status["pywb_visual_replay_status"]
        result["WACZ_REPLAY_STATUS"] = replay_status["wacz_replay_status"]
        result["WACZ_VISUAL_REPLAY_STATUS"] = replay_status["wacz_visual_replay_status"]
    return replay_status


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python source_warc_replay_hardening.py <closeout-output-root>")
        raise SystemExit(2)
    root = Path(sys.argv[1])
    report = integrate_replay_hardening_for_closeout(result={"output_root": str(root)})
    print(json.dumps(report, indent=2, ensure_ascii=False))
