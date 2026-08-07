# Shared source Adapter Artifact Intake

This stage converts a completed Adapter Capture Session plus explicit local artifact file bindings into validated shared Source Artifact Collection packages.

It verifies the operator-supplied files against the capture session receipt metadata, hashes only the explicitly named files, builds per-adapter source artifact collections, and writes a collection handoff for extraction.

Safety boundary: it does not fetch URLs, launch browsers, scan folders, read credentials, submit archives, upload releases, mutate app files, mutate registry files, or start live/manual actions. It only reads explicit operator-supplied local artifact paths and records safe basenames, byte counts, and SHA-256 hashes.
