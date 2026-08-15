from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twitter_media_backend import (  # noqa: E402
    build_twitter_media_backend_plan,
    build_twitter_shared_media_backend_request,
)


def _write_manifest(path: Path, tested: bool = False) -> None:
    path.write_text(
        json.dumps(
            {
                "capabilities": {
                    "twitter.com": {
                        "tested": tested,
                        "plugins": [{"plugin_name": "TwitterCom", "plugin_type": "hoster"}],
                    },
                    "x.com": {
                        "tested": tested,
                        "plugins": [{"plugin_name": "TwitterCom", "plugin_type": "hoster"}],
                    },
                }
            }
        ),
        encoding="utf-8",
    )


def main() -> None:
    media_url = "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
    with tempfile.TemporaryDirectory(prefix="ytce_v72g_direct_media_strict_") as tmp:
        manifest_path = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest_path, tested=False)
        strict_plan = build_twitter_media_backend_plan(
            source_url=media_url,
            output_dir=Path(tmp) / "strict_downloads",
            capability_manifest_path=manifest_path,
            allow_untested_jdownloader=False,
        )
        assert strict_plan.execution_allowed is False
        assert strict_plan.blocked_reason
        assert "not marked tested" in strict_plan.blocked_reason
        try:
            build_twitter_shared_media_backend_request(strict_plan)
        except ValueError as exc:
            assert "not marked tested" in str(exc)
        else:
            raise AssertionError("strict direct media plan unexpectedly built an executable request")

        permissive_plan = build_twitter_media_backend_plan(
            source_url=media_url,
            output_dir=Path(tmp) / "permissive_downloads",
            capability_manifest_path=Path(tmp) / "missing_manifest.json",
            allow_untested_jdownloader=True,
        )
        request = build_twitter_shared_media_backend_request(permissive_plan)
        assert permissive_plan.execution_allowed is True
        assert permissive_plan.blocked_reason == ""
        assert request.source_adapter_id == "twitter_x_direct_media"
        assert request.source_url == media_url

    print("assert_twitter_direct_media_strict_block_v72g OK")


if __name__ == "__main__":
    main()
