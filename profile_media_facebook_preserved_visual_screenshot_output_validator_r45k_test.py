#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
import tempfile
import zlib
from pathlib import Path

import profile_media_facebook_preserved_visual_screenshot_output_validator_r45k as r45k


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    import binascii
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)


def write_rgb_png(path: Path, width: int, height: int, draw_black: bool = False) -> None:
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            if draw_black and 10 <= x <= width - 10 and 10 <= y <= height - 10:
                row.extend((20, 20, 20))
            else:
                row.extend((255, 255, 255))
        rows.append(b"\x00" + bytes(row))
    payload = b"".join(rows)
    data = b"\x89PNG\r\n\x1a\n"
    data += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += _png_chunk(b"IDAT", zlib.compress(payload))
    data += _png_chunk(b"IEND", b"")
    path.write_bytes(data)


def make_receipt(run_dir: Path, screenshot_path: Path | None, *, safety_ok: bool = True, text_ok: bool = True) -> Path:
    text_path = run_dir / "facebook_preserved_visual_clean_visible_text.txt"
    text_path.write_text("Loaded Facebook-rendered comment text\n" if text_ok else "", encoding="utf-8")
    side_effects = dict(r45k.REQUIRED_SAFE_SIDE_EFFECT_FLAGS)
    if not safety_ok:
        side_effects["cookie_or_token_extraction_performed"] = True
    side_effects.update({
        "browser_session_started": True,
        "network_actions_performed": True,
    })
    contract = dict(r45k.REQUIRED_SAFE_CONTRACT_FLAGS)
    receipt = {
        "marker": r45k.R45J_MARKER,
        "status": "PASS_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER",
        "run_dir": str(run_dir),
        "preserved_visual_clean_text_path": str(text_path),
        "preserved_visual_full_screenshot_path": str(screenshot_path) if screenshot_path else None,
        "preserved_visual_tile_screenshot_paths": [],
        "contract": contract,
        "side_effect_flags": side_effects,
    }
    receipt_path = run_dir / "r45j_facebook_preserved_visual_screenshot_runner_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt_path


def assert_status(report, expected):
    assert report["status"] == expected, json.dumps(report, indent=2)


def test_passing_nonblank_image():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        image = root / "facebook_preserved_visual_full_page.png"
        write_rgb_png(image, 80, 60, draw_black=True)
        receipt = make_receipt(root, image)
        report = r45k.validate_receipt_path(receipt)
        assert_status(report, r45k.STATUS_PASS)
        assert report["screenshot_checks"][0]["non_near_white_ratio"] > 0.002


def test_failing_blank_white_image():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        image = root / "facebook_preserved_visual_full_page.png"
        write_rgb_png(image, 80, 60, draw_black=False)
        receipt = make_receipt(root, image)
        report = r45k.validate_receipt_path(receipt)
        assert_status(report, r45k.STATUS_BLOCKED)
        assert report["screenshot_checks"][0]["reason"] == "screenshot_appears_blank_or_near_white"


def test_missing_screenshot_case():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt = make_receipt(root, None)
        report = r45k.validate_receipt_path(receipt)
        assert_status(report, r45k.STATUS_BLOCKED)
        assert any(c.get("reason") == "no_preserved_visual_screenshot_path_in_receipt" for c in report["checks"])


def test_safety_contract_failure_case():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        image = root / "facebook_preserved_visual_full_page.png"
        write_rgb_png(image, 80, 60, draw_black=True)
        receipt = make_receipt(root, image, safety_ok=False)
        report = r45k.validate_receipt_path(receipt)
        assert_status(report, r45k.STATUS_BLOCKED)
        assert any(c.get("name") == "r45j_side_effect_cookie_or_token_extraction_performed" and c.get("status") == "fail" for c in report["safety_checks"])


def test_self_test_contract_flags():
    flags = r45k.side_effect_flags()
    assert flags["browser_session_started"] is False
    assert flags["network_actions_performed"] is False
    assert flags["hidden_platform_api_scraping_performed"] is False
    assert r45k.contract()["artifact_only_rule"]


if __name__ == "__main__":
    test_passing_nonblank_image()
    test_failing_blank_white_image()
    test_missing_screenshot_case()
    test_safety_contract_failure_case()
    test_self_test_contract_flags()
    print("profile_media_facebook_preserved_visual_screenshot_output_validator_r45k_test: PASS")
