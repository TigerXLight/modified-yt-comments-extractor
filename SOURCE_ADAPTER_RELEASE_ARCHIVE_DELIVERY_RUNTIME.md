# Source Adapter Release Archive Delivery Runtime

Status: `SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RUNTIME_BUILT`

This implementation executes the local delivery runtime for accepted source-adapter evidence/export artifacts.

Implemented artifacts:

- `SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_PLAN_READY` with twenty delivery rows: five named sites multiplied by four delivery targets.
- `SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RECEIPTS_READY` with twenty written local delivery receipt rows.
- `SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RUNTIME_READY_FOR_OPERATOR_RECEIPT_CLOSEOUT` handoff status.

Delivery targets implemented in this runtime:

1. evidence queue output,
2. Total Export source package output,
3. release index output,
4. archive handoff output.

The runtime writes JSON delivery outputs atomically under a supplied output directory, records byte counts and SHA-256 hashes, and preserves `KEYS/ACCOUNTS` redacted credential-reference handling.
