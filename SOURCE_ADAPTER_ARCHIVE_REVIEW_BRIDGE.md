# Shared Source Adapter Archive Review Bridge

`source_adapter_archive_review_bridge.py` connects Adapter Archive Result Intake Bridge batches to the shared `source_archive_review` builder.

The section supports shared reviewer decisions and per-archive-result-intake decisions for multi-adapter batches, writes five bridge artifacts, verifies each shared archive-review package, and hands approved archive reviews to the shared `source_pipeline_closeout` stage.

This is an implementation bridge: it performs the shared archive-review packaging logic, preserves review decisions and archive receipt traceability, and keeps live/provider/archive execution concerns explicit in the structured package fields.
