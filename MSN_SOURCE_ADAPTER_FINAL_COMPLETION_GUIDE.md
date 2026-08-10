# MSN Source Adapter Final Completion Guide

Current completion path:

1. Build or collect an MSN output folder from the adapter pipeline.
2. Run the operator final runner against that folder.
3. Run the final validation, done-gate, acceptance, closeout, final-lock, evidence-seal, and release-candidate tools as needed.
4. Fill the manual/live acceptance result JSON after checking a real MSN article/comments/media/archive case.
5. Run `source_msn_adapter_release_promotion.py`.

The adapter is not promoted to real MSN `COMPLETE` unless the release promotion report says `COMPLETE`.

The release promotion report says `COMPLETE` only when:

- the filled live/manual evidence file is positive;
- all required manual/live checks pass;
- no no-network report in the output folder is failing/blocking;
- source-chain review is explicitly passed, preserving MSN as republisher surface where applicable and not confusing visible publisher/media credit/original source.

This protects the earlier source-evidence rule:

- MSN page = captured platform / republisher surface.
- Visible publisher such as The Independent = publisher/source visible on the MSN page.
- Visible media credit such as Google Street View = media credit, not automatically original source for every claim.
- Original source is only original when actually located or evidenced.

Use this guide as the final handoff boundary before moving to the next roadmap item.
