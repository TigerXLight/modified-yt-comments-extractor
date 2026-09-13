# R42GM Preview Surface Integration Notes

Marker: `YTCE_R42GM_PREVIEW_SURFACE_INTEGRATION`

Status target: `PASS_R42GM_PREVIEW_SURFACE_INTEGRATION`

## Scope

R42GM exposes the R42GL/R42GK read-only evidence-bundle-plan preview inside the existing preview surface. It does not replace `profile_media_source_package_preview.py`, `profile_media_source_intake.py`, `source_resource_state.py`, `source_adapters.py`, source-role policy, counters, no-jump behavior, or review-window matching.

## Existing Path Reused

- `profile_media_source_package_preview.py` remains the source package preview builder.
- `source_package_preview_payload(preview)` remains the existing dataclass-to-payload surface.
- `source_resource_state.py` remains the pasted URL / batch TXT row source.
- `profile_media_existing_source_intake_bundle_preview_r42gl.py` remains the bridge from existing row/preview shapes into R42GK planning.
- R42GM delegates evidence bundle planning to R42GL/R42GK and adds only an additive `evidence_bundle_plan_preview` plus compact `evidence_bundle_plan_preview_surface` summary.

## Integration Point

`profile_media_preview_surface_integration_r42gm.py` adds:

- `enrich_source_package_preview_surface_read_only(value)`;
- `preview_surface_payload_from_source_row(value)`;
- `preview_surface_payload_from_source_url_intake(result)`;
- `build_preview_surface_payload(value)`;
- `render_preview_surface_summary_text(payload)`.

The package preview enrichment returns a copied payload and does not mutate the input. Existing fields such as `batch_payload`, `source_package_preview`, `artifacts`, source-role policy, link-source objects, and claim-span previews remain present.

## Guardrails

The R42GM surface is preview-only and metadata-only. It performs no live capture, browser/WebView2/CDP launch, downloader execution, JDownloader execution, media download, archive submission, CAPTCHA/security bypass, credential/cookie/token access, source-role assignment, review-window rewrite, counter mutation, or no-jump mutation.

Unknown/private/prohibited rows remain review-only and non-promoted. Global Player/LBC keeps the R42GH public audio/catch-up method metadata as a plan only: `yt_dlp_python_module`, `py -m yt_dlp`, format `0`, `m4a`, native M4A preservation, and sidecars. X/Twitter `examaddaorg` keeps the observed 6.7k/8.9 MB benchmark as context only, not a hard limit.
