from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twitter_media_backend import (  # noqa: E402
    build_twitter_media_backend_plan,
    build_twitter_shared_media_backend_request,
    is_twitter_direct_media_url,
    normalize_twitter_media_source_url,
)


def main() -> None:
    media_url = "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
    with tempfile.TemporaryDirectory(prefix="ytce_v72f_direct_media_assert_") as tmp:
        plan = build_twitter_media_backend_plan(
            source_url=f"[{media_url}]({media_url})",
            output_dir=Path(tmp) / "downloads",
            capability_manifest_path=Path(tmp) / "missing_manifest.json",
            allow_untested_jdownloader=False,
        )
        request = build_twitter_shared_media_backend_request(plan)

    assert normalize_twitter_media_source_url(f"<{media_url}>") == media_url
    assert is_twitter_direct_media_url(media_url) is True
    assert plan.canonical_url == media_url
    assert plan.execution_allowed is True
    assert plan.blocked_reason == ""
    assert plan.source_id == "pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
    assert request.source_adapter_id == "twitter_x_direct_media"
    assert request.source_url == media_url
    print("assert_twitter_direct_media_backend_v72f OK")


if __name__ == "__main__":
    main()
