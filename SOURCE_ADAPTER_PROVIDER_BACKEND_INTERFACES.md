# Source Adapter Provider Backend Interfaces

Status: `SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_BUILT`

This milestone implements the executable provider-backend interface layer that sits after the operator-approved execution runtime. It is not another roadmap-only artifact: it builds request rows and executes local receipt-writing backend handlers for `credential_lookup`, `browser_capture`, `archive_submit`, `release_upload`, and `file_library_publish`.

The handoff status is `SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_READY_FOR_GUI_CONTROLLER_AND_PROVIDER_SPECIFIC_BACKENDS`.

## Implemented surfaces

- Provider backend registry with callable handler names.
- Provider backend request matrix with 25 request rows.
- Local executable receipt backend producing 25 backend execution receipts.
- Redacted credential-reference ledger preservation through `KEYS/ACCOUNTS`.
- Store, CLI, verifier, and docs tests.

## Next implementation

The next patch should wire these provider backend interfaces into GUI/controller dispatch and then replace local executable receipt handlers with provider-specific backends where configured. Raw secrets remain outside receipts; `KEYS/ACCOUNTS` stores references and receipts keep redacted hashes.
