from evidence_schema import CaptureMethod, EvidenceProvenance
from source_capture_plan import (
    PLAN_STATUS_READY,
    PLAN_STATUS_UNSUPPORTED_SOURCE,
    build_source_capture_plan,
)
from source_plan_provenance import (
    manifest_with_plan_provenance,
    provenance_from_source_capture_plan,
)
from total_export_manifest import TotalExportManifest


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    plan = build_source_capture_plan(
        source_url=f"https://youtu.be/{VALID_ID}?t=30s",
        source_label="Clip",
        selected_capture_options=["comments"],
    )
    assert plan.status == PLAN_STATUS_READY

    provenance = provenance_from_source_capture_plan(plan)
    assert isinstance(provenance, EvidenceProvenance)
    assert provenance.source_url == CANONICAL_URL
    assert provenance.canonical_url == CANONICAL_URL
    assert provenance.source_platform == "youtube"
    assert provenance.adapter_name == "youtube"
    assert provenance.item_id == VALID_ID
    assert provenance.permalink == CANONICAL_URL
    assert provenance.capture_method == CaptureMethod.UNKNOWN
    assert "Source Capture Plan status: ready" in provenance.verification_notes
    assert "no fetch/capture performed" in provenance.verification_notes

    existing = EvidenceProvenance(source_url="https://example.com/original")
    manifest = TotalExportManifest(
        package_id="test-package",
        source_urls=[CANONICAL_URL],
        capture_options=["comments"],
        provenance_records=[existing],
        notes="Keep me.",
    )
    updated_manifest = manifest_with_plan_provenance(manifest, plan)
    assert manifest.provenance_records == [existing]
    assert updated_manifest.package_id == "test-package"
    assert updated_manifest.source_urls == [CANONICAL_URL]
    assert updated_manifest.capture_options == ["comments"]
    assert updated_manifest.notes == "Keep me."
    assert len(updated_manifest.provenance_records) == 2
    assert updated_manifest.provenance_records[0] is existing
    assert updated_manifest.provenance_records[1].source_url == CANONICAL_URL

    unsupported_plan = build_source_capture_plan(
        source_url="https://example.com/article",
        source_label="Example article",
        selected_capture_options=["comments"],
    )
    assert unsupported_plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
    unsupported_provenance = provenance_from_source_capture_plan(unsupported_plan)
    assert unsupported_provenance.source_url == "https://example.com/article"
    assert unsupported_provenance.canonical_url == ""
    assert unsupported_provenance.source_platform == ""
    assert unsupported_provenance.adapter_name == ""
    assert unsupported_provenance.item_id == ""
    assert unsupported_provenance.permalink == "https://example.com/article"
    assert "unsupported_source" in unsupported_provenance.verification_notes


if __name__ == "__main__":
    run_self_test()
    print("Source plan provenance self-test passed.")
