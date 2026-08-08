# Source Adapter Regression Queue Runtime Wiring

This milestone installs the promoted Source Adapter priority fixture regression queue into deterministic local runtime wiring artifacts.

It is intentionally local-only and dry-run-only. It does not run live smoke, browser automation, network calls, API calls, archive provider submission, release upload, file-library mutation, credential storage, cookie storage, broad folder scanning, or real GUI mutation. In plain terms: no live smoke, no browser automation, no network/API calls, no real archive submission, no release upload, no file-library mutation, no credential storage, and not GUI mutation. It records local regression runner queue rows, expanded controller/provider bindings, GUI/controller call-site wiring rows, and metadata-only local acceptance receipts.

## Scope

- Builds `SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING_BUILT` from the prior priority fixture regression promotion package and runtime GUI/provider implementation package.
- Installs the 20 promoted rows into `SOURCE_ADAPTER_LOCAL_REGRESSION_RUNNER_QUEUE_INSTALLED`.
- Expands controller/provider route bindings into `SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_EXPANDED_BINDINGS_READY` for local dry-run coverage.
- Wires planned GUI/controller call sites as `SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITES_WIRED_FOR_LOCAL_DRY_RUN` without mutating the GUI.
- Records `SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPTS_READY` metadata-only receipts for the 20 local runner rows.
- Carries the five named-site smoke rows forward as `SOURCE_ADAPTER_NAMED_SITE_SMOKE_APPROVAL_GATE_CARRIED_FORWARD_UNEXECUTED`.
- Produces `SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING_READY_FOR_CLOSEOUT_AUDIT` when all verifier checks pass.

## Preserved counts and surfaces

The deterministic example package preserves:

- 20 local regression runner queue rows.
- 20 expanded controller/provider binding rows.
- 20 local regression acceptance receipt rows.
- 4 GUI/controller call-site runtime wiring rows.
- 5 named-site smoke gate carry-forward rows.
- The article/news page, social post/thread, comments/replies thread, media transcript/ASR source, and archive provider receipt fixture families.
- The archive submit, release upload, file library publish, and credential lookup provider capabilities.
- The `KEYS/ACCOUNTS` label, credential reference selector surface, and redacted reference-hash requirements.

## Safety boundaries

This milestone is not operator live smoke execution and not GUI mutation. Named-site smoke remains approval-gated and unexecuted.

The verifier fails if:

- A local runner row claims anything other than `dry_run`.
- Any queue, binding, GUI wiring, receipt, or smoke row enables live execution, provider calls, network access, release upload, archive submission, file-library mutation, or credential storage.
- Any acceptance receipt has missing expected fields or is not accepted for closeout audit.
- Any named-site smoke row is marked approved or executed.
- The `KEYS/ACCOUNTS` label or redacted credential-reference handling is lost.
- Any forbidden secret-like field such as API keys, passwords, tokens, cookies, authorization headers, raw credentials, or private keys appears.

## Operator handoff

After this milestone, the safe next step is a closeout audit and roadmap/current-state update over the local regression queue wiring artifacts. Any real named-site smoke, browser automation, archive provider call, release upload, or credential-bearing provider execution still requires a separate explicit operator approval step.
