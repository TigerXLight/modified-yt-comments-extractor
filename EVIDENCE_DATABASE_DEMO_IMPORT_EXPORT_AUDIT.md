# Evidence Database Phase 4 Demo Import/Export Audit

Date: 2026-07-16

Checkpoint: `8f96a0a Document evidence database UI scaffold`

## Scope

Evidence Database Phase 4 adds fixture-only demonstration data and
non-destructive review-session import/export around the existing standalone
review scaffold.

This phase remains synthetic, local, review-only, dry-run-only, and
explicit-record-only. It does not approve broad user-folder scanning, real
evidence file movement, automatic classification execution, live site capture,
archive/provider calls, downloads, scraping, browser automation, credential
access, provider/network behavior, or sensitive-attribute inference.

## Current Gap

The repository now has:

- Phase 1 model/index contracts and temp-root atomic JSON storage.
- Phase 2 review/session/root/preview/decision/apply-plan contracts.
- Phase 3 standalone review-window/controller scaffold.

It does not yet have a safe built-in demonstration dataset for the scaffold, or
a deterministic JSON package that can export and re-import a review session,
preview rows, decisions, and a non-executing apply plan for tests and future UI
review work.

## Fixture Data Decision

Add only synthetic fixture records with synthetic root metadata and safe
example source URLs. The fixture must cover the existing review states:

- `unknown`
- `not_evidenced`
- `proposed`
- `user_confirmed`
- `rejected`
- `superseded`

The fixture must not include real user evidence paths, real local filesystem
roots, credentials, browser/profile paths, cookies, authorization headers, or
sensitive-attribute classifications.

## Import/Export Decision

Add JSON-only review-session export/import helpers. Exports should include
schema/version fields, deterministic payload hashing, session state, preview
state, decisions, and non-executing apply-plan metadata.

Imports must validate schema/version and safety flags, reject malformed or
destructive-looking payloads, and return reconstructed review objects without
executing imported decisions, scanning folders, moving files, or applying
classification changes.

## Safety Notes

- Synthetic fixture data is for local tests and scaffold demos only.
- Imported apply plans remain non-executing.
- User confirmation remains required for future real workflows.
- Destructive actions remain unimplemented.
- Visible `main.py` placement remains deferred unless a later hook is trivial
  and non-invasive.
