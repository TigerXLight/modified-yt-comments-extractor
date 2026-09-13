# R42GL Existing Source Intake Preview Bridge Audit Notes

Marker: `YTCE_R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT`

Status target: `PASS_R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT`

## Scope

R42GL inspects the existing source-intake and source-package-preview path, then adds a standalone read-only bridge from existing row/preview shapes into the R42GK evidence-bundle-plan preview contract. It does not replace `profile_media_source_intake.py`, `profile_media_source_package_preview.py`, `source_resource_state.py`, `source_adapters.py`, source-role policy, or review-window behavior.

## Existing Path Found

- `profile_media_source_intake.py` contains the guarded `ProfileMediaSourceIntakePlan` dry-run/apply flow.
- `source_resource_state.py` contains URL/token intake via `parse_source_url_intake` and row creation via `build_source_resource_row`, producing `SourceResourceRowState` rows.
- `profile_media_source_package_preview.py` contains the existing `ProfileMediaSourcePackagePreview` builder and the `batch_payload["source_package_preview"]` preview section used by database import/review flows.
- `source_adapters.py` contains source adapter metadata/family handling for existing source row canonicalization.
- Source-role policy and matching remain separate and are not called for role assignment by this bridge.

## Bridge Implemented

`profile_media_existing_source_intake_bundle_preview_r42gl.py` consumes existing dataclass/dictionary shapes and converts them to the R42GK `SourceRowInput` contract only for preview planning. It then calls R42GK to produce an optional `evidence_bundle_plan_preview` summary with:

- source row id / source candidate id;
- canonical/raw URL;
- R42GK evidence bundle id and plan id;
- planned root/manifest/review-string/source-role bridge paths;
- review-string preview links;
- source-role bridge preview;
- media candidate ids and child paths;
- promotion status and side-effect boundary.

The helper `enrich_source_package_preview_payload_read_only()` returns a copied payload with the preview section attached. It does not mutate the original preview payload.

## Guardrails

The bridge is preview-only and metadata-only. It performs no network fetch, browser launch, WebView2/CDP session, downloader execution, extension execution, archive submission, CAPTCHA/security bypass, credential/cookie/token access, source-role assignment, counter/no-jump mutation, or review-window rewrite.
