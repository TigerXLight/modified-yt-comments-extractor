# Source Adapter Release Review Acceptance Runtime

This implementation milestone adds concrete callable Python runtime surfaces for the shared Source Adapter execution pipeline. It keeps `KEYS/ACCOUNTS` as the credential-reference surface and writes redacted references and receipt hashes only.

The runtime is designed to connect operator-approved named-site execution, provider-specific adapters, browser capture, archive submission, release upload, file-library publishing, evidence export, Total Export packaging, and receipt review in one connected implementation chain.

Status strings covered by tests:

- `SOURCE_ADAPTER_RELEASE_REVIEW_ACCEPTANCE_RUNTIME_BUILT`
- runtime handoff ready status
- verifier issue count equals zero
