# Credential Security Audit and Row 2A Architecture

Date: 2026-07-12

Checkpoint reviewed: `447f031 Close Access Keys presentation milestone`

## Scope

This is the approved row 2A architecture and existing-code audit only.

It adds no credential values, storage reads or writes, migration, clearing, reveal/copy UI, connection tests, provider/API calls, OAuth, browser access, network access, or runtime wiring. The existing YouTube API-key behavior remains unchanged.

The machine-readable, non-secret companion model is `credential_architecture.py`; its focused validation is `credential_architecture_test.py`.

## Existing Baseline

The current application has one operational credential path for the YouTube Data API key:

- `main.py` owns a masked sidebar entry, an eye/reveal button, a storage-status label, and load/save calls.
- `core/settings.py` places the key in `AppSettings`, prefers the optional operating-system keyring, and otherwise permits a plaintext `settings.json` fallback.
- `core/constants.py` defines one keyring service/account pair for the YouTube key.
- `requirements.txt` includes `keyring` as an optional secure-storage dependency.
- `.gitignore` excludes `settings.json` and `.env`, which reduces accidental commits but does not make plaintext storage secure.
- The Access & Keys catalog and window are non-secret presentation metadata and do not inspect the configured value.

## Findings

### R2A-001 — High: silent plaintext downgrade

When keyring is absent or a keyring operation fails, `SettingsManager` changes its internal mode and can serialize the API key into `settings.json`. A later credential implementation must fail closed for persistent writes rather than silently choosing plaintext.

### R2A-002 — High: incomplete clear behavior

`delete_api_key()` deletes the keyring item when keyring is active, but it does not remove an `api_key` field from legacy plaintext settings. A later clear workflow must address every known backend, report partial failure, and avoid claiming success while another copy remains.

### R2A-003 — Medium: secret/general-settings coupling

`AppSettings` carries the API key beside ordinary filter, sort, and window preferences. A provider-neutral credential boundary should keep secret material out of general settings objects and serializers.

### R2A-004 — Medium: long-lived full value in the GUI

The current YouTube key is loaded into a GUI entry and can be fully revealed. This behavior must be preserved until a separately approved migration, but the future manager should prefer presence/masked state and a temporary explicit reveal action.

### R2A-005 — Medium: one global credential mapping

The current constants and manager support one fixed YouTube keyring account. Cloud ASR and future adapters need stable credential IDs and backend locator metadata before any values are accepted.

### R2A-006 — Medium: no provenance or migration state

The current load path does not expose a non-secret record of which backend supplied the value or whether fallback occurred. A later abstraction should return backend/presence/error-category metadata without returning values to reporting code.

### R2A-007 — Low: storage label can become stale

The sidebar storage label is created from a one-time storage-info string. If keyring fails later, that label may no longer match the actual backend state.

### R2A-008 — Low: no central diagnostic-redaction boundary

Current credential errors are logged from exception text. Future provider SDK errors must be normalized and redacted before logs or UI because request details can contain sensitive material.

## Approved Architecture Rules

1. Use stable credential IDs independent of UI labels and provider SDK objects.
2. Keep non-secret descriptors separate from credential material.
3. Allow session-memory material only through an explicit action.
4. Treat environment variables as read-only inputs; never write or migrate into them.
5. Prefer an operating-system keyring for explicitly approved persistent writes.
6. Never silently fall back from keyring to plaintext.
7. Treat legacy plaintext settings as compatibility/audit input only, never a destination for new writes.
8. Never migrate, overwrite, or clear a credential without an explicit user action and visible result.
9. Report presence, backend, support, and connection-test status as separate non-secret states.
10. Keep connection tests and provider runs explicit and outside row 2A.
11. Never place credential material in exports, evidence packages, logs, manifests, sidecars, screenshots, captured text, command output, source control, telemetry, or automatic clipboard operations.
12. A later clear operation must target every known backend and report partial failure without exposing values.
13. A later reveal/copy action must be separate, temporary, and user-triggered.
14. Cloud credentials do not by themselves approve network calls, provider integration, upload of media, cost, or privacy behavior.

## Initial Non-Secret Credential Registry

Row 2A defines identifiers only for:

- YouTube Data API key.
- ElevenLabs Scribe API key.
- AssemblyAI API key.
- Deepgram API key.
- Speechmatics API key.
- Azure Speech account credentials.
- Google STT provider-defined credentials.
- Cohere API key.
- AWS Transcribe account credentials.

The registry contains environment-variable names and the existing YouTube keyring/legacy field identifiers where known. It contains no values and performs no reads.

## Storage Policy Order

The architecture records this policy order without implementing it:

1. Explicit session memory.
2. Read-only environment source.
3. Explicit operating-system keyring persistence.
4. Legacy plaintext settings as audit/compatibility input only.

The order is not an automatic resolution algorithm. No fallback or migration is permitted by row 2A.

## Later Approval Boundaries

Row 2A does not authorize the following:

- **Row 2B:** runtime credential-provider abstraction, read-only non-secret presence/provenance status, safe diagnostic categories, and fail-closed backend behavior.
- **Row 2C:** masked entry/save/clear UI, explicit migration from the current YouTube field, legacy plaintext cleanup, and temporary reveal/copy controls.
- **Later separate boundary:** explicit connection tests, provider calls, OAuth, cloud ASR upload/run behavior, or any network access.

No later row should begin merely because this audit exists.
