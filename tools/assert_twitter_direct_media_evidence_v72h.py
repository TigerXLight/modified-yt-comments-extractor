from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tempfile import TemporaryDirectory

from twitter_media_backend import (
    build_twitter_media_backend_plan,
    twitter_direct_media_capability_evidence_status,
)

DIRECT_URL = "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"


def _write_manifest(path: Path, *, tested: bool = False) -> None:
    path.write_text(
        json.dumps(
            {
                "capabilities": {
                    "twitter.com": {
                        "tested": tested,
                        "plugins": [{"plugin_name": "TwitterCom"}],
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def test_missing_evidence_keeps_strict_direct_media_blocked() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = root / "jd_capabilities_manifest.json"
        _write_manifest(manifest, tested=False)
        plan = build_twitter_media_backend_plan(
            source_url=DIRECT_URL,
            output_dir=root / "out",
            capability_manifest_path=manifest,
            allow_untested_jdownloader=False,
            direct_media_capability_evidence_path=root / "missing.json",
        )
        assert plan.execution_allowed is False
        assert "no direct Twitter media JD evidence is recorded" in plan.blocked_reason


def test_valid_evidence_allows_strict_direct_media() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = root / "jd_capabilities_manifest.json"
        _write_manifest(manifest, tested=False)
        evidence = root / "evidence.json"
        evidence.write_text(
            json.dumps(
                {
                    "schema_version": "twitter_direct_media_jd_capability_evidence.v72h",
                    "tested": True,
                    "source_url": DIRECT_URL,
                    "observed_host": "x.com",
                    "status": "success",
                    "phase": "completed",
                    "files_count": 1,
                    "api3128_used": True,
                    "route_used": "api3128",
                    "manifest_path": str(root / "jdownloader-internal-download-manifest.json"),
                }
            ),
            encoding="utf-8",
        )
        status = twitter_direct_media_capability_evidence_status(evidence)
        assert status.tested is True
        plan = build_twitter_media_backend_plan(
            source_url=DIRECT_URL,
            output_dir=root / "out",
            capability_manifest_path=manifest,
            allow_untested_jdownloader=False,
            direct_media_capability_evidence_path=evidence,
        )
        assert plan.execution_allowed is True
        assert plan.blocked_reason == ""
        assert plan.direct_media_capability_evidence is not None
        assert plan.direct_media_capability_evidence.tested is True


def test_invalid_evidence_does_not_allow_strict_direct_media() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = root / "jd_capabilities_manifest.json"
        _write_manifest(manifest, tested=False)
        evidence = root / "evidence.json"
        evidence.write_text(
            json.dumps(
                {
                    "tested": True,
                    "source_url": DIRECT_URL,
                    "status": "success",
                    "files_count": 1,
                    "api3128_used": False,
                    "route_used": "flashgot",
                }
            ),
            encoding="utf-8",
        )
        assert twitter_direct_media_capability_evidence_status(evidence).tested is False
        plan = build_twitter_media_backend_plan(
            source_url=DIRECT_URL,
            output_dir=root / "out",
            capability_manifest_path=manifest,
            allow_untested_jdownloader=False,
            direct_media_capability_evidence_path=evidence,
        )
        assert plan.execution_allowed is False


if __name__ == "__main__":
    test_missing_evidence_keeps_strict_direct_media_blocked()
    test_valid_evidence_allows_strict_direct_media()
    test_invalid_evidence_does_not_allow_strict_direct_media()
    print("assert_twitter_direct_media_evidence_v72h OK")
