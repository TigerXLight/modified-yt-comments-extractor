#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_final_signoff_gate import build_signoff_report, write_signoff_report


def _seed_repo(repo: Path) -> None:
    for name in [
        "source_msn_adapter_manifest.py",
        "source_msn_adapter_total_package.py",
        "source_msn_adapter_completion_cli.py",
        "source_msn_adapter_done_gate.py",
        "source_msn_adapter_acceptance_suite.py",
        "source_msn_adapter_final_validator.py",
        "source_msn_adapter_operator_final_runner.py",
        "source_msn_adapter_live_validation_index.py",
        "source_msn_adapter_media_download_cli.py",
        "source_msn_adapter_certification_archive.py",
        "source_msn_adapter_readiness.py",
        "source_msn_adapter_release_report.py",
        "source_msn_adapter_final_evidence_seal.py",
        "source_msn_adapter_final_operator_packet.py",
        "source_msn_adapter_live_evidence_validator.py",
        "source_msn_adapter_release_promotion.py",
        "source_msn_adapter_final_promotion_closeout.py",
        "source_msn_adapter_certification_bundle.py",
    ]:
        (repo / name).write_text("x\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        output = Path(td) / "output"
        reports = Path(td) / "reports"
        repo.mkdir()
        output.mkdir()
        _seed_repo(repo)
        for name in ["article.json", "comments.json", "rendered-page.html", "capture.warc.gz", "media_inventory.json", "source_manifest.json"]:
            (output / name).write_text("{}\n", encoding="utf-8")
        pending = build_signoff_report(repo, output)
        assert pending.signoff_state == "SIGNOFF_PENDING_POSITIVE_LIVE_EVIDENCE"
        (output / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json").write_text(
            json.dumps({"status": "SIGNED_OFF_WITH_POSITIVE_LIVE_EVIDENCE", "passed": True, "all_required_checks_passed": True}),
            encoding="utf-8",
        )
        signed = build_signoff_report(repo, output)
        assert signed.live_completion_allowed is True
        assert signed.signoff_state == "SIGNED_OFF_WITH_POSITIVE_LIVE_EVIDENCE"
        paths = write_signoff_report(signed, reports, repo, output)
        for key in ("json", "markdown", "csv", "trace_json", "trace_markdown", "trace_csv"):
            assert Path(paths[key]).exists(), key
        md = (reports / "MSN_SOURCE_ADAPTER_FINAL_SIGNOFF_GATE.md").read_text(encoding="utf-8")
        assert "No-network self-tests alone are insufficient" in md
    print("MSN final signoff gate self-test passed.")


if __name__ == "__main__":
    main()
