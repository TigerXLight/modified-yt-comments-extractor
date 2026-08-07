from pathlib import Path
from tempfile import TemporaryDirectory

from source_content_extraction import SourceContentArtifact, build_source_content_extraction
from source_content_extraction_verifier import verify_source_content_extraction


def test_verifier_accepts_valid_extraction_and_rejects_paths() -> None:
    with TemporaryDirectory() as td:
        artifact = Path(td) / "article.txt"
        artifact.write_text("Title\nBody text.", encoding="utf-8")
        extraction = build_source_content_extraction(
            adapter_id="verify_adapter",
            source_url="https://verify.example/item",
            artifacts=[SourceContentArtifact("article_text", str(artifact))],
        )
        valid = verify_source_content_extraction(extraction)
        assert valid["verified"] is True
        broken = dict(extraction)
        broken["leaked"] = "C:\\Users\\example\\article.txt"
        invalid = verify_source_content_extraction(broken)
        assert invalid["verified"] is False
        assert "full_local_path_serialized" in invalid["issues"]


if __name__ == "__main__":
    test_verifier_accepts_valid_extraction_and_rejects_paths()
    print("Source content extraction verifier self-test passed.")
