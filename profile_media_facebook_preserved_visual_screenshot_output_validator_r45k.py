#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

MARKER = "YTCE_R45K_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_OUTPUT_VALIDATOR"
STATUS_PASS = "PASS_R45K_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_OUTPUT_VALIDATOR"
STATUS_BLOCKED = "BLOCKED_R45K_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_OUTPUT_VALIDATOR"
SCHEMA_VERSION = "facebook_preserved_visual_screenshot_output_validator.r45k.v1"

R45J_MARKER = "YTCE_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r45k_facebook_preserved_visual_screenshot_output_validator"
DEFAULT_R45J_OUTPUT_ROOT = "profile_media_live_captures/r45j_facebook_preserved_visual_screenshot_runner"

REQUIRED_SAFE_SIDE_EFFECT_FLAGS = {
    "hidden_platform_api_scraping_performed": False,
    "login_automation_performed": False,
    "cookie_or_token_extraction_performed": False,
    "browser_profile_files_read_or_copied": False,
    "browser_profile_files_parsed_by_tool": False,
    "webview2_storage_or_cookie_inspection_performed": False,
    "remote_media_downloads_performed": False,
}

REQUIRED_SAFE_CONTRACT_FLAGS = {
    "hidden_platform_api_scraping_enabled": False,
    "login_automation_enabled": False,
    "cookie_or_token_extraction_enabled": False,
    "browser_profile_file_copying_enabled": False,
    "browser_profile_file_parsing_enabled": False,
    "webview2_storage_or_cookie_inspection_enabled": False,
    "remote_media_downloads_enabled": False,
}


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def contract() -> Dict[str, Any]:
    return {
        "marker": MARKER,
        "mode_id": "facebook_preserved_visual_screenshot_output_validator",
        "schema_version": SCHEMA_VERSION,
        "primary_route": "Read an existing local R45J output directory or receipt and validate that preserved visual screenshots are present, non-empty, not blank/white, and supported by non-empty visible text exports.",
        "artifact_only_rule": "R45K does not launch a browser, navigate, click visible page controls, inspect browser profiles, or perform network actions; it only reads local R45J output artifacts.",
        "blank_page_rule": "Fail screenshot validation only for missing/unreadable/empty images, invalid dimensions, or an extremely low non-near-white pixel ratio consistent with a blank white page.",
        "r45j_safety_receipt_rule": "The referenced R45J receipt must confirm no hidden platform API scraping, login automation, cookie/token extraction, browser profile reading/copying/parsing, WebView2 storage inspection, or remote media downloads.",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def side_effect_flags() -> Dict[str, Any]:
    return {
        "browser_session_started": False,
        "network_actions_performed": False,
        "visible_page_auto_expand_clicks_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "browser_profile_files_read_or_copied": False,
        "browser_profile_files_parsed_by_tool": False,
        "webview2_storage_or_cookie_inspection_performed": False,
        "remote_media_downloads_performed": False,
        "facebook_preserved_visual_screenshot_output_validator_invoked": True,
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _is_windows_abs(value: str) -> bool:
    return len(value) >= 3 and value[1] == ":" and value[2] in "\\/"


def _resolve_artifact_path(value: Any, receipt_dir: Path) -> Optional[Path]:
    if not value:
        return None
    raw = str(value)
    p = Path(raw)
    if p.exists():
        return p
    # If a receipt was moved between machines, allow basename-local recovery for tests/audits.
    candidate = receipt_dir / p.name
    if candidate.exists():
        return candidate
    if not p.is_absolute() and not _is_windows_abs(raw):
        candidate = receipt_dir / raw
        if candidate.exists():
            return candidate
    return p


def _candidate_receipts(root: Path) -> List[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    patterns = [
        "r45j_facebook_preserved_visual_screenshot_runner_receipt.json",
        "*r45j*preserved*visual*receipt*.json",
        "*facebook_preserved_visual*receipt*.json",
        "*receipt*.json",
    ]
    seen = set()
    out: List[Path] = []
    for pattern in patterns:
        for p in root.rglob(pattern):
            key = str(p.resolve()) if p.exists() else str(p)
            if key not in seen and p.is_file():
                seen.add(key)
                out.append(p)
    return sorted(out, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)


def find_receipt(receipt: Optional[str], output_dir: str) -> Optional[Path]:
    if receipt:
        p = Path(receipt)
        return p if p.exists() else p
    candidates = _candidate_receipts(Path(output_dir))
    return candidates[0] if candidates else None


def _iter_screenshot_values(receipt: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    for key in (
        "preserved_visual_full_screenshot_path",
        "full_screenshot_path",
        "screenshot_path",
    ):
        value = receipt.get(key)
        if value:
            values.append(str(value))
    for key in (
        "preserved_visual_tile_screenshot_paths",
        "tile_screenshot_paths",
        "screenshot_paths",
    ):
        value = receipt.get(key)
        if isinstance(value, list):
            values.extend(str(v) for v in value if v)
    # Preserve order while deduping.
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _iter_text_values(receipt: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    for key in (
        "preserved_visual_clean_text_path",
        "pre_clean_inner_text_path",
        "inner_text_path",
        "text_path",
        "visible_text_path",
    ):
        value = receipt.get(key)
        if value:
            values.append(str(value))
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _pixel_metrics_from_pixels(width: int, height: int, pixels: Iterable[Tuple[int, int, int, int]], total_pixels: int, sampled_pixels: int) -> Dict[str, Any]:
    if width <= 0 or height <= 0:
        return {
            "width": width,
            "height": height,
            "total_pixels": total_pixels,
            "sampled_pixels": 0,
            "non_near_white_pixels": 0,
            "near_white_pixels": 0,
            "non_near_white_ratio": 0.0,
            "near_white_ratio": 1.0,
            "mean_rgb": [255.0, 255.0, 255.0],
            "valid_dimensions": False,
        }
    non_white = 0
    near_white = 0
    count = 0
    rs = gs = bs = 0
    for r, g, b, a in pixels:
        count += 1
        rs += r
        gs += g
        bs += b
        # Transparent pixels should not rescue a blank screenshot.
        is_near_white = (a <= 16) or (r >= 248 and g >= 248 and b >= 248)
        if is_near_white:
            near_white += 1
        else:
            non_white += 1
    denom = max(1, count)
    return {
        "width": width,
        "height": height,
        "total_pixels": total_pixels,
        "sampled_pixels": count,
        "non_near_white_pixels": non_white,
        "near_white_pixels": near_white,
        "non_near_white_ratio": non_white / denom,
        "near_white_ratio": near_white / denom,
        "mean_rgb": [round(rs / denom, 2), round(gs / denom, 2), round(bs / denom, 2)],
        "valid_dimensions": width > 0 and height > 0,
    }


def _analyze_with_pillow(path: Path, max_sample_pixels: int) -> Optional[Dict[str, Any]]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
        width, height = rgba.size
        total = width * height
        step = max(1, int(math.sqrt(max(1, total) / max(1, max_sample_pixels))))
        sampled = []
        for y in range(0, height, step):
            for x in range(0, width, step):
                sampled.append(rgba.getpixel((x, y)))
        metrics = _pixel_metrics_from_pixels(width, height, sampled, total, len(sampled))
        metrics["decoder"] = "pillow"
        metrics["sample_step"] = step
        return metrics


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _png_chunks(data: bytes) -> Iterable[Tuple[bytes, bytes]]:
    pos = 8
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        start = pos + 8
        end = start + length
        if end + 4 > len(data):
            raise ValueError("truncated PNG chunk")
        yield typ, data[start:end]
        pos = end + 4
        if typ == b"IEND":
            break


def _analyze_png_pure(path: Path, max_sample_pixels: int) -> Dict[str, Any]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG image and Pillow is unavailable")
    width = height = bit_depth = color_type = None
    idat = bytearray()
    for typ, payload in _png_chunks(data):
        if typ == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", payload)
            if compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("unsupported PNG compression/filter/interlace")
        elif typ == b"IDAT":
            idat.extend(payload)
    if width is None or height is None or bit_depth != 8 or color_type not in (0, 2, 6):
        raise ValueError("unsupported PNG format without Pillow")
    channels = {0: 1, 2: 3, 6: 4}[int(color_type)]
    bpp = channels
    raw = zlib.decompress(bytes(idat))
    stride = int(width) * channels
    offset = 0
    prev = bytearray(stride)
    rows: List[bytearray] = []
    for _y in range(int(height)):
        ftype = raw[offset]
        offset += 1
        row = bytearray(raw[offset:offset + stride])
        offset += stride
        recon = bytearray(stride)
        for i, val in enumerate(row):
            left = recon[i - bpp] if i >= bpp else 0
            up = prev[i]
            up_left = prev[i - bpp] if i >= bpp else 0
            if ftype == 0:
                recon[i] = val
            elif ftype == 1:
                recon[i] = (val + left) & 0xFF
            elif ftype == 2:
                recon[i] = (val + up) & 0xFF
            elif ftype == 3:
                recon[i] = (val + ((left + up) // 2)) & 0xFF
            elif ftype == 4:
                recon[i] = (val + _paeth(left, up, up_left)) & 0xFF
            else:
                raise ValueError(f"unsupported PNG filter type {ftype}")
        rows.append(recon)
        prev = recon
    total = int(width) * int(height)
    step = max(1, int(math.sqrt(max(1, total) / max(1, max_sample_pixels))))

    def sampled_pixels() -> Iterable[Tuple[int, int, int, int]]:
        for y in range(0, int(height), step):
            row = rows[y]
            for x in range(0, int(width), step):
                base = x * channels
                if color_type == 0:
                    g = row[base]
                    yield (g, g, g, 255)
                elif color_type == 2:
                    yield (row[base], row[base + 1], row[base + 2], 255)
                else:
                    yield (row[base], row[base + 1], row[base + 2], row[base + 3])

    metrics = _pixel_metrics_from_pixels(int(width), int(height), sampled_pixels(), total, 0)
    metrics["decoder"] = "pure_png"
    metrics["sample_step"] = step
    return metrics


def analyze_image(path: Path, min_nonwhite_ratio: float = 0.002, max_sample_pixels: int = 200_000) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
        "status": "fail",
        "warnings": [],
    }
    if not path.exists():
        result["reason"] = "screenshot_file_missing"
        return result
    if result["file_size_bytes"] <= 0:
        result["reason"] = "screenshot_file_empty"
        return result
    try:
        metrics = _analyze_with_pillow(path, max_sample_pixels)
        if metrics is None:
            metrics = _analyze_png_pure(path, max_sample_pixels)
        result.update(metrics)
        if not metrics.get("valid_dimensions"):
            result["reason"] = "invalid_image_dimensions"
        elif float(metrics.get("non_near_white_ratio") or 0.0) < min_nonwhite_ratio:
            result["reason"] = "screenshot_appears_blank_or_near_white"
        else:
            result["status"] = "pass"
            result["reason"] = "screenshot_has_visible_non_white_content"
    except Exception as e:
        result["reason"] = "screenshot_unreadable"
        result["error"] = str(e)
    return result


def validate_text_exports(receipt: Dict[str, Any], receipt_dir: Path) -> List[Dict[str, Any]]:
    values = _iter_text_values(receipt)
    checks: List[Dict[str, Any]] = []
    if not values:
        return [{"name": "visible_text_export_present", "status": "fail", "reason": "no_visible_text_export_path_in_receipt"}]
    for value in values:
        p = _resolve_artifact_path(value, receipt_dir)
        exists = bool(p and p.exists())
        size = p.stat().st_size if exists else 0
        text_nonempty = False
        snippet = ""
        if exists:
            text = p.read_text(encoding="utf-8", errors="replace")
            snippet = " ".join(text.split())[:160]
            text_nonempty = bool(text.strip())
        checks.append({
            "name": "visible_text_export_non_empty",
            "path": str(p) if p else value,
            "exists": exists,
            "file_size_bytes": size,
            "text_nonempty": text_nonempty,
            "snippet": snippet,
            "status": "pass" if exists and size > 0 and text_nonempty else "fail",
            "reason": "visible_text_export_ok" if exists and size > 0 and text_nonempty else "visible_text_export_missing_or_empty",
        })
    return checks


def validate_safety_receipt(receipt: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    side_flags = receipt.get("side_effect_flags") if isinstance(receipt.get("side_effect_flags"), dict) else {}
    contract_flags = receipt.get("contract") if isinstance(receipt.get("contract"), dict) else {}
    for key, expected in REQUIRED_SAFE_SIDE_EFFECT_FLAGS.items():
        actual = side_flags.get(key, None)
        checks.append({
            "name": f"r45j_side_effect_{key}",
            "expected": expected,
            "actual": actual,
            "status": "pass" if actual is expected else "fail",
        })
    for key, expected in REQUIRED_SAFE_CONTRACT_FLAGS.items():
        actual = contract_flags.get(key, None)
        checks.append({
            "name": f"r45j_contract_{key}",
            "expected": expected,
            "actual": actual,
            "status": "pass" if actual is expected else "fail",
        })
    return checks


def validate_receipt_path(receipt_path: Path, min_nonwhite_ratio: float = 0.002, max_sample_pixels: int = 200_000) -> Dict[str, Any]:
    warnings: List[str] = []
    checks: List[Dict[str, Any]] = []
    if not receipt_path.exists():
        report = {
            "marker": MARKER,
            "status": STATUS_BLOCKED,
            "schema_version": SCHEMA_VERSION,
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "receipt_path": str(receipt_path),
            "checks": [{"name": "r45j_receipt_exists", "status": "fail", "reason": "receipt_missing"}],
            "warnings": warnings,
            "contract": contract(),
            "side_effect_flags": side_effect_flags(),
        }
        return report

    receipt = _read_json(receipt_path)
    receipt_dir = receipt_path.parent
    marker_actual = receipt.get("marker")
    checks.append({
        "name": "r45j_receipt_exists",
        "path": str(receipt_path),
        "status": "pass",
    })
    checks.append({
        "name": "r45j_receipt_marker",
        "expected": R45J_MARKER,
        "actual": marker_actual,
        "status": "pass" if marker_actual == R45J_MARKER else "warn",
    })
    if marker_actual != R45J_MARKER:
        warnings.append("receipt_marker_is_not_r45j_expected_marker")

    screenshot_values = _iter_screenshot_values(receipt)
    screenshot_checks: List[Dict[str, Any]] = []
    if not screenshot_values:
        screenshot_checks.append({
            "name": "preserved_visual_screenshot_present",
            "status": "fail",
            "reason": "no_preserved_visual_screenshot_path_in_receipt",
        })
    else:
        for value in screenshot_values:
            p = _resolve_artifact_path(value, receipt_dir)
            screenshot_checks.append(analyze_image(p if p else Path(value), min_nonwhite_ratio=min_nonwhite_ratio, max_sample_pixels=max_sample_pixels))
    checks.extend(screenshot_checks)

    text_checks = validate_text_exports(receipt, receipt_dir)
    checks.extend(text_checks)

    safety_checks = validate_safety_receipt(receipt)
    checks.extend(safety_checks)

    # Warn, but do not fail, if the R45J capture itself launched a browser/network to make visible screenshots.
    side_flags = receipt.get("side_effect_flags") if isinstance(receipt.get("side_effect_flags"), dict) else {}
    if side_flags.get("browser_session_started"):
        warnings.append("r45j_browser_session_started_expected_for_live_capture_validator_did_not_start_browser")
    if side_flags.get("network_actions_performed"):
        warnings.append("r45j_network_actions_performed_expected_when_r45j_navigated_validator_did_not_use_network")

    fail_count = sum(1 for c in checks if c.get("status") == "fail")
    status = STATUS_PASS if fail_count == 0 else STATUS_BLOCKED
    return {
        "marker": MARKER,
        "status": status,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "receipt_path": str(receipt_path),
        "r45j_receipt_status": receipt.get("status"),
        "run_dir": receipt.get("run_dir"),
        "min_nonwhite_ratio": min_nonwhite_ratio,
        "checks": checks,
        "screenshot_checks": screenshot_checks,
        "text_checks": text_checks,
        "safety_checks": safety_checks,
        "fail_count": fail_count,
        "warnings": warnings,
        "contract": contract(),
        "side_effect_flags": side_effect_flags(),
    }


def run_validation(args: argparse.Namespace) -> Dict[str, Any]:
    receipt_path = find_receipt(args.receipt, args.output_dir)
    if receipt_path is None:
        report = {
            "marker": MARKER,
            "status": STATUS_BLOCKED,
            "schema_version": SCHEMA_VERSION,
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "output_dir": args.output_dir,
            "checks": [{"name": "r45j_receipt_discovered", "status": "fail", "reason": "no_r45j_receipt_found"}],
            "warnings": [],
            "contract": contract(),
            "side_effect_flags": side_effect_flags(),
        }
    else:
        report = validate_receipt_path(Path(receipt_path), min_nonwhite_ratio=args.min_nonwhite_ratio, max_sample_pixels=args.max_sample_pixels)
    report_root = Path(args.report_output_root)
    report_path = report_root / f"r45k_facebook_preserved_visual_screenshot_output_validator_report_{utc_stamp()}.json"
    report["report_path"] = _write_json(report_path, report)
    print(MARKER)
    print(report.get("status"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    checks = [
        {"name": "artifact_only_contract", "status": "pass" if contract().get("hidden_platform_api_scraping_enabled") is False else "fail"},
        {"name": "safe_side_effect_flags", "status": "pass" if all(side_effect_flags().get(k) is v for k, v in REQUIRED_SAFE_SIDE_EFFECT_FLAGS.items()) else "fail"},
        {"name": "png_fallback_available", "status": "pass" if callable(_analyze_png_pure) else "fail"},
        {"name": "receipt_discovery_available", "status": "pass" if callable(find_receipt) else "fail"},
    ]
    report = {
        "marker": MARKER,
        "status": STATUS_PASS if all(c["status"] == "pass" for c in checks) else STATUS_BLOCKED,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "checks": checks,
        "contract": contract(),
        "side_effect_flags": side_effect_flags(),
    }
    report_path = Path(args.report_output_root) / "r45k_self_test_report.json"
    report["report_path"] = _write_json(report_path, report)
    print(MARKER)
    print(report.get("status"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R45K local validator for R45J preserved visual screenshot outputs")
    ap.add_argument("--output-dir", default=DEFAULT_R45J_OUTPUT_ROOT, help="R45J output root or run directory to search for a receipt")
    ap.add_argument("--receipt", default=None, help="Explicit R45J receipt JSON path")
    ap.add_argument("--report-output-root", default=DEFAULT_OUTPUT_ROOT, help="Directory for the R45K validation report")
    ap.add_argument("--min-nonwhite-ratio", type=float, default=0.002, help="Minimum sampled non-near-white pixel ratio required for a screenshot to pass")
    ap.add_argument("--max-sample-pixels", type=int, default=200000, help="Approximate maximum pixels sampled per image")
    ap.add_argument("--self-test", action="store_true", help="Run static self-test without requiring an R45J run")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = run_self_test(args) if args.self_test else run_validation(args)
    return 0 if report.get("status") == STATUS_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
