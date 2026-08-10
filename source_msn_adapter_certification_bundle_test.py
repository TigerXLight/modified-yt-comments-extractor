from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_certification_bundle import (
    CERTIFIED_COMPLETE,
    RC_PENDING,
    build_certification_bundle,
    write_certification_bundle,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_certification_waits_for_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "article.json", "{}")
        _write(root / "comments.json", "{}")
        _write(root / "profiles.json", "{}")
        _write(root / "rendered-page.html", "<html></html>")
        _write(root / "media_inventory.json", "{}")
        _write(root / "source_chain_manifest.json", "{}")
        _write(root / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.json", json.dumps({"lock_state": "RC_LOCKED_PENDING_LIVE_EVIDENCE"}))

        bundle = build_certification_bundle(root)
        assert bundle.decision == RC_PENDING
        assert any("live evidence" in warning.lower() for warning in bundle.warnings)

        out = root / "out"
        paths = write_certification_bundle(bundle, out)
        assert paths["json"].exists()
        assert paths["markdown"].exists()
        assert paths["csv"].exists()


def test_certification_promotes_with_positive_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "article.json", "{}")
        _write(root / "comments.json", "{}")
        _write(root / "profiles.json", "{}")
        _write(root / "rendered-page.html", "<html></html>")
        _write(root / "archive.warc.gz", "warc")
        _write(root / "media_inventory.json", "{}")
        _write(root / "source_chain_manifest.json", "{}")
        _write(root / "MSN_SOURCE_ADAPTER_PROMOTION_REPORT.json", json.dumps({"decision": "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"}))
        _write(root / "MSN_LIVE_EVIDENCE_RESULT.json", json.dumps({
            "checks": {
                "article_extraction": "PASS",
                "comments_profile_extraction": "PASS",
                "offline_viewer_archive": "PASS",
                "media_registration_download_status": "PASS",
                "source_chain_provenance": "PASS",
            }
        }))

        bundle = build_certification_bundle(root)
        assert bundle.decision == CERTIFIED_COMPLETE
        assert [c for c in bundle.checks if c.check_id == "live_evidence"][0].status == "PASS"


if __name__ == "__main__":
    test_certification_waits_for_live_evidence()
    test_certification_promotes_with_positive_live_evidence()
    print("MSN certification bundle self-test passed.")
