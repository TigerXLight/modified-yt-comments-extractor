from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_article_extraction import extract_msn_manual_article
from capture_msn_manual_capture_bundle import build_msn_manual_capture_bundle
from capture_msn_manual_capture_bundle_store import store_msn_manual_capture_bundle


def test_store_writes_bundle_and_safe_manifest_without_paths() -> None:
    article = extract_msn_manual_article(source_url="https://www.msn.com/example", artifact_text="Title\nThis is article body text copied by the operator.")
    bundle = build_msn_manual_capture_bundle(article=article)
    with tempfile.TemporaryDirectory() as tmp:
        result = store_msn_manual_capture_bundle(output_dir=tmp, bundle=bundle, file_prefix="msn_bundle")
        assert len(result.files) == 2
        assert {item.file_name for item in result.files} == {"msn_bundle.json", "msn_bundle_manifest.json"}
        payload = json.loads((Path(tmp) / "msn_bundle.json").read_text(encoding="utf-8"))
        assert payload["article_text"].startswith("This is article")
        assert str(tmp) not in json.dumps(result.to_dict())


if __name__ == "__main__":
    test_store_writes_bundle_and_safe_manifest_without_paths()
    print("MSN manual capture bundle store self-test passed.")
