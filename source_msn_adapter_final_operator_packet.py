#!/usr/bin/env python3
"""Final operator packet generator for MSN source adapter.

Creates a final operator packet for a repository or MSN output folder. The
packet is conservative: it can say the repo is ready for live evidence, but it
does not say COMPLETE unless a positive live-evidence result is present.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

from source_msn_adapter_final_artifact_manifest import build_manifest, write_manifest


@dataclass(frozen=True)
class PacketCheck:
    check: str
    status: str
    detail: str


@dataclass(frozen=True)
class OperatorPacket:
    generated_at_utc: str
    repo_root: str
    output_root: str
    final_state: str
    live_completion_allowed: bool
    checks: List[PacketCheck]
    commands: List[str]


def _find_live_evidence(output_root: Path) -> Path | None:
    candidates = [
        output_root / "MSN_LIVE_EVIDENCE_RESULT.json",
        output_root / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json",
        output_root / "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    matches = sorted(output_root.rglob("*LIVE*EVIDENCE*RESULT*.json"))
    return matches[0] if matches else None


def _live_evidence_positive(path: Path | None) -> bool:
    if not path or not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    text = json.dumps(data, ensure_ascii=False).lower()
    positive_tokens = [
        "complete_with_positive_live_evidence",
        "positive_live_evidence",
        '"passed": true',
        '"pass": true',
        '"status": "pass"',
        '"status": "passed"',
    ]
    negative_tokens = ["blocked", "fail", "failed", "missing"]
    if any(tok in text for tok in positive_tokens) and not any(tok in text for tok in negative_tokens):
        return True
    return False


def build_operator_packet(repo_root: Path, output_root: Path) -> OperatorPacket:
    repo = Path(repo_root).resolve()
    out = Path(output_root).resolve()
    manifest = build_manifest(repo)
    live_path = _find_live_evidence(out)
    live_positive = _live_evidence_positive(live_path)

    checks: List[PacketCheck] = [
        PacketCheck(
            "repo_artifact_manifest",
            "PASS" if manifest.repository_state == "READY_FOR_LIVE_EVIDENCE" else "PARTIAL",
            f"{manifest.present_count}/{manifest.total_expected} expected repo artifacts present",
        ),
        PacketCheck(
            "live_evidence_file",
            "PASS" if live_path else "PENDING",
            str(live_path) if live_path else "No live evidence result file found",
        ),
        PacketCheck(
            "positive_live_evidence",
            "PASS" if live_positive else "PENDING",
            "Positive live evidence found" if live_positive else "No positive live evidence result found",
        ),
        PacketCheck(
            "completion_boundary",
            "PASS",
            "No COMPLETE state is allowed without positive live evidence.",
        ),
    ]

    if live_positive:
        final_state = "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
    elif manifest.repository_state == "READY_FOR_LIVE_EVIDENCE":
        final_state = "RC_LOCKED_PENDING_LIVE_EVIDENCE"
    else:
        final_state = "READY_FOR_LIVE_EVIDENCE"

    commands = [
        'python source_msn_adapter_operator_quickstart.py --repo-root . --output-root "<MSN_OUTPUT_FOLDER>"',
        'python source_msn_adapter_live_evidence_template.py --out-dir "<MSN_OUTPUT_FOLDER>\\live_evidence"',
        'python source_msn_adapter_release_promotion.py --output-root "<MSN_OUTPUT_FOLDER>"',
        'python source_msn_adapter_certification_bundle.py --output-root "<MSN_OUTPUT_FOLDER>"',
        'python source_msn_adapter_final_operator_packet.py --repo-root . --output-root "<MSN_OUTPUT_FOLDER>"',
    ]

    return OperatorPacket(
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        repo_root=str(repo),
        output_root=str(out),
        final_state=final_state,
        live_completion_allowed=live_positive,
        checks=checks,
        commands=commands,
    )


def write_operator_packet(packet: OperatorPacket, out_dir: Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_PACKET.json"
    md_path = out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_PACKET.md"
    csv_path = out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_PACKET_CHECKS.csv"
    cmd_path = out / "RUN_MSN_FINAL_OPERATOR_PACKET_COMMANDS.cmd"

    json_path.write_text(json.dumps(asdict(packet), indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# MSN Source Adapter Final Operator Packet",
        "",
        f"- Generated UTC: `{packet.generated_at_utc}`",
        f"- Final state: `{packet.final_state}`",
        f"- Live completion allowed: `{packet.live_completion_allowed}`",
        "",
        "## Completion boundary",
        "",
        "No no-network self-test or repo artifact manifest can promote MSN to complete. "
        "Final completion requires positive manual/live evidence.",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in packet.checks:
        md_lines.append(f"| {check.check} | {check.status} | {check.detail} |")
    md_lines.extend(["", "## Command order", ""])
    for i, cmd in enumerate(packet.commands, 1):
        md_lines.append(f"{i}. `{cmd}`")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        for check in packet.checks:
            writer.writerow(asdict(check))

    cmd_lines = [
        "@echo off",
        "setlocal",
        "echo MSN final operator packet command sequence",
        "echo Replace ^<MSN_OUTPUT_FOLDER^> with the real MSN output folder before running commands.",
    ]
    for cmd in packet.commands:
        cmd_lines.append("echo " + cmd)
    cmd_path.write_text("\r\n".join(cmd_lines) + "\r\n", encoding="utf-8")

    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path), "cmd": str(cmd_path)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate final MSN operator packet.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--output-root", default=".", help="MSN output folder or staging folder.")
    parser.add_argument("--out-dir", default="msn_final_operator_packet", help="Output directory.")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    packet = build_operator_packet(Path(args.repo_root), Path(args.output_root))
    manifest_paths = write_manifest(build_manifest(Path(args.repo_root)), out_dir)
    packet_paths = write_operator_packet(packet, out_dir)
    print(f"MSN final operator packet state: {packet.final_state}")
    print(f"Packet JSON: {packet_paths['json']}")
    print(f"Manifest JSON: {manifest_paths['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
