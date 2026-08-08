# Source Adapter Operator Approved Execution Runtime

This milestone moves beyond queue/audit planning into an actual callable operator-approved execution runtime.

The runtime builds and executes the local provider-adapter implementation path for the five named-site smoke families:

- article / news page
- social post / thread
- comments / replies thread
- media transcript / ASR source
- archive provider receipt

It consumes the runtime queue closeout audit and regression queue runtime wiring packages, then creates:

- an operator approval packet
- an executable named-site queue
- executed operator-approved rows
- provider execution receipts
- a redacted `KEYS/ACCOUNTS` credential reference ledger
- a runtime handoff for GUI/provider integration

This is not plan-only. The local filesystem adapter writes concrete receipt JSON artifacts for browser capture, archive submission, release upload, file-library publishing, and credential-reference lookup. Those adapter interfaces are the implementation seam for replacing the local backend with browser/provider/archive/release/library backends when those concrete provider integrations are wired.

The current default backend is `local_filesystem_adapter` so tests can execute deterministically without external services. This does not remove network/browser/archive/upload/library/provider execution from the roadmap. Those capabilities remain implementation scope and are expected to be wired through the same callable runtime and receipt contracts.

Credential handling stays under `KEYS/ACCOUNTS`: receipts contain credential reference IDs and redacted reference hashes only. Raw credential material must not be persisted in packages, logs, or receipts.

Important status strings:

- `SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_BUILT`
- `SOURCE_ADAPTER_OPERATOR_APPROVAL_PACKET_READY`
- `SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_QUEUE_READY`
- `SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_EXECUTED`
- `SOURCE_ADAPTER_PROVIDER_EXECUTION_RECEIPTS_RECORDED`
- `SOURCE_ADAPTER_REDACTED_CREDENTIAL_REFERENCE_LEDGER_RECORDED`
- `SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_READY_FOR_PROVIDER_AND_GUI_INTEGRATION`

The next implementation step is direct GUI/controller connection and provider-specific backend replacement, not another abstract planning milestone.

All capabilities remain implementation scope; this milestone supplies the callable execution seam rather than removing later provider work.

all capabilities remain implementation scope.
