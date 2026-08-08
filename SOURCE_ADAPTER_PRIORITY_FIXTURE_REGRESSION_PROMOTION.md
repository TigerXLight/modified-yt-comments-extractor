# Source Adapter Priority Fixture Regression Promotion

This milestone promotes the accepted Source Adapter Priority Fixture Pack Implementation receipts into the regular deterministic regression queue.

It is intentionally a local, fake, dry-run regression-promotion package. It does not run live smoke, browser automation, network calls, API calls, archive provider submission, release upload, file-library mutation, credential storage, cookie storage, or broad folder scanning. In plain terms: no live smoke, no browser automation, no network/API calls, no real archive submission, no release upload, no file-library mutation, and no credential storage.

## Scope

- Builds `SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION_BUILT` from the previous priority fixture pack implementation package.
- Promotes accepted priority fixture pack dispatch receipts into `SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_QUEUE_READY`.
- Converts the GUI installation checklist into `SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITE_INSTALLATION_PLAN_READY` call-site installation planning rows.
- Carries named-site smoke rows forward as `SOURCE_ADAPTER_NAMED_SITE_SMOKE_REMAINS_OPERATOR_APPROVAL_REQUIRED` without execution.
- Produces a handoff status of `SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION_READY_FOR_REGRESSION_QUEUE_INSTALLATION` when verification passes.

## Preserved counts and surfaces

The deterministic example package preserves:

- 5 priority fixture pack families.
- 20 promoted regular regression queue rows.
- 20 source dispatch receipt rows.
- 4 GUI/controller call-site installation planning rows.
- 5 named-site smoke approval-gate rows.
- The adapter/source families for article/news page, social post/thread, comments/replies thread, media transcript/ASR source, and archive provider receipt.
- The provider capabilities for archive submit, release upload, file library publish, and credential lookup.
- The `KEYS/ACCOUNTS` label, the credential reference selector surface, and redacted reference-hash handling.

## Safety boundaries

This milestone is not operator live smoke execution. Named-site smoke remains approval-gated and unexecuted. The package only prepares local regression queue rows and deterministic installation planning rows.

The verifier fails if:

- A promoted row claims live execution or anything other than `dry_run`.
- A named-site smoke row is marked executed or operator-approved.
- A required dispatch receipt field is missing.
- The `KEYS/ACCOUNTS` label or credential selector surface is lost.
- Any forbidden secret-like field such as API keys, passwords, tokens, cookies, or authorization headers appears.
- Counts drift from 5 fixture packs, 20 promoted regression rows, or 5 named-site smoke gate rows.

## Operator handoff

After this milestone, the next safe step is to install or wire the local regression queue and GUI/controller call-site plan. Operator named-site smoke execution still requires a separate explicit approval step with named sites, operator input references, and preserved receipts.
