# MSN Source Adapter Release Candidate Lock

This document defines the repo-side release-candidate lock for the MSN source adapter.

The lock is intentionally conservative.  It can say the repo-side adapter is locked as a release candidate, but it does not call real/live MSN complete without a positive operator/manual result from a named MSN article.

## What this layer checks

- Required MSN adapter modules and documentation exist.
- Repo-side files are hashed into a SHA256 index.
- Article extraction, comments/profile extraction, offline viewer/archive handling, media registration, and source-chain provenance each have an owning module.
- The output clearly distinguishes no-network fixture confidence from live MSN evidence.

## Command

```cmd
python source_msn_adapter_release_candidate_lock.py --repo-root . --output-dir msn_release_candidate_lock
```

With a filled live/manual result:

```cmd
python source_msn_adapter_release_candidate_lock.py --repo-root . --output-dir msn_release_candidate_lock --manual-live-result path	o\MSN_LIVE_ACCEPTANCE_RESULT.json
```

## Completion rule

No-network tests can lock the release candidate.  A real MSN COMPLETE claim requires positive manual/live evidence.
