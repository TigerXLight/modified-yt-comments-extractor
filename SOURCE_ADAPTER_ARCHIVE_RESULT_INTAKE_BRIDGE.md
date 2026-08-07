# Shared Source Adapter Archive Result Intake Bridge

`source_adapter_archive_result_intake_bridge.py` bridges Adapter Archive Handoff Bridge batches into the shared `source_archive_result_intake` stage.

It consumes `source_adapter_archive_handoff_bridge_v1` packages, groups operator archive result records by archive handoff, builds one shared archive-result-intake output per archive handoff, and emits `READY_FOR_SHARED_ARCHIVE_REVIEW` handoff metadata for the shared archive review stage.

Outputs include the bridge package, archive result-intake output batch, archive result-intake batch rows, archive review batch handoff, operator summary, store receipts, CLI, verifier, docs, and tests.
