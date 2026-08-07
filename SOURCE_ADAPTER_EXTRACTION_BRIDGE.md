# Shared source Adapter Extraction Bridge

This section turns validated `source_adapter_artifact_intake` output into shared content/comment extraction outputs.

It consumes an Artifact Intake package plus explicit local artifact file bindings, revalidates byte counts and SHA-256 hashes, runs the shared content/comment extraction modules, and writes a capture-bundle handoff with status `READY_FOR_SHARED_CAPTURE_BUNDLE`.

The stage is local/operator-boundary only: it does not fetch URLs, does not launch browsers, does not scan folders, does not read credentials, does not submit archives, does not upload releases, and does not mutate app or registry files.

Full local artifact paths are used only for explicit local reads and are not serialized in the produced review/release documents.
