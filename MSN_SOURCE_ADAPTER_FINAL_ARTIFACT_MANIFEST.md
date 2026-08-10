# MSN Source Adapter Final Artifact Manifest

This module creates a SHA256-indexed inventory of the MSN adapter files in the repository.

The manifest is designed for later roadmap work. It makes it easier to see whether a future patch accidentally removes or weakens MSN adapter files, docs, live-evidence gates, or regression smoke files.

## Outputs

- `MSN_SOURCE_ADAPTER_FINAL_ARTIFACT_MANIFEST.json`
- `MSN_SOURCE_ADAPTER_FINAL_ARTIFACT_MANIFEST.md`
- `MSN_SOURCE_ADAPTER_FINAL_ARTIFACT_MANIFEST.csv`

## Boundary

Presence of artifacts proves repo coverage, not live MSN completion. Live completion still requires positive manual/live evidence.
