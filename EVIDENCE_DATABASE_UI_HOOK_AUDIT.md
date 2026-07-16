# Evidence Database Phase 3 UI Hook Audit

Date: 2026-07-16

Checkpoint: `c55ec010 Document evidence database review workflow`

## Scope

Evidence Database Phase 3 resolves the previously deferred review UI hook while
staying inside the existing local-only review boundary.

This phase remains review-only, dry-run-only, and explicit-record-only. It does
not approve broad user-folder scanning, real indexing of arbitrary folders,
automatic classification execution, evidence file movement, live site capture,
archive/provider calls, downloads, scraping, browser automation, credential
access, or sensitive-attribute inference.

## Current UI Insertion Options

### Standalone Review Scaffold

This is the cleanest current hook. A separate review-window/controller scaffold
can consume the existing `evidence_database_review.py` contracts, expose counts
and dry-run status in tests, and avoid disturbing the main sidebar and runtime
layout.

Decision: use this option first.

### Existing FILES/EXPORT Area

The current sidebar order is:

```text
UPDATES
KEYS/ACCOUNTS
EXPORT
FILES
```

`main_source_resource_ui_test.py` explicitly protects that order, and the
FILES/EXPORT areas are already active user workflows. Adding a visible Evidence
Database control there would mix review-only database scaffolding with export
and session-file actions.

Decision: defer visible placement here.

### Controller-Only Factory

Phase 2 already provides controller-level review/session/root/preview/decision
and non-executing apply-plan contracts. A controller-only factory would preserve
safety, but it would not resolve the UI scaffold gap by itself.

Decision: keep the Phase 2 controller contracts and add a standalone scaffold
layer above them.

## EDUIH0 Decision

Add a standalone Evidence Database review scaffold in a separate module. Do not
expand `main.py` unless a later focused check finds a visible hook that does not
change sidebar order or disturb FILES, EXPORT, KEYS/ACCOUNTS, ASR, Total Export,
Source Resource, or operational capture workflows.

## Safety Notes

- The scaffold must display a plain-language dry-run/review-only warning.
- It must report that destructive actions are not implemented.
- It must not scan folders or discover files.
- It must not move files or apply classification changes.
- It must use only explicitly supplied review records and controller data.
