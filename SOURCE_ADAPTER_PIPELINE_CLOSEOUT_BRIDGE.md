# Shared Source Adapter Pipeline Closeout Bridge

`source_adapter_pipeline_closeout_bridge.py` completes the shared adapter flow by taking Adapter Archive Review Bridge output and routing each approved archive review closeout through the shared `source_pipeline_closeout` stage.

The bridge produces a deterministic closeout package batch, a batch index, a roadmap closeout handoff, an operator summary, CLI/store/verifier support, and fixtures for multi-adapter batches. Runtime-capable surfaces remain represented as explicit stage records and operator-approved handoffs so future source adapters can reuse the same flow instead of cloning the MSN-specific path.
