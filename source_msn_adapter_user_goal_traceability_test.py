#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_user_goal_traceability import build_goal_traceability, write_goal_traceability


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        out = Path(td) / "out"
        reports = Path(td) / "reports"
        repo.mkdir()
        out.mkdir()
        for name in [
            "source_msn_adapter_manifest.py",
            "source_msn_adapter_total_package.py",
            "source_msn_adapter_completion_cli.py",
            "source_msn_adapter_done_gate.py",
            "source_msn_adapter_acceptance_suite.py",
            "source_msn_adapter_media_download_cli.py",
            "source_msn_adapter_live_evidence_validator.py",
            "source_msn_adapter_release_promotion.py",
            "source_msn_adapter_final_promotion_closeout.py",
            "source_msn_adapter_certification_bundle.py",
            "source_msn_adapter_final_operator_packet.py",
        ]:
            (repo / name).write_text("x\n", encoding="utf-8")
        (out / "article.json").write_text("{}\n", encoding="utf-8")
        (out / "comments.json").write_text("{}\n", encoding="utf-8")
        (out / "media_inventory.json").write_text("{}\n", encoding="utf-8")
        (out / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json").write_text("{}\n", encoding="utf-8")
        report = build_goal_traceability(repo, out)
        assert report.total_goals == 5
        assert report.overall_state in {             'GOAL_TRACEABILITY_READY',             'GOAL_TRACEABILITY_PARTIAL',             'GOAL_TRACEABILITY_PENDING_POSITIVE_LIVE_EVIDENCE',             'READY_FOR_LIVE_EVIDENCE',             'RC_LOCKED_PENDING_LIVE_EVIDENCE',             'SIGNOFF_PENDING_POSITIVE_LIVE_EVIDENCE',         }, report.overall_state
