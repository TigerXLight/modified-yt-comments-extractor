# R43U-prep Twitter/X baseline count clarity

This note locks the R43T pushed baseline before the universal social ledger contract is extracted.

## Why

The real Twitter/X smoke can observe the same image URL through multiple live evidence surfaces:
visible DOM/article extraction, R42GV visible observation stores, R42GT packages, and runner inventory.
R43T should retain raw observation candidate counts for auditability, while the account ledger
should also expose the deduped media item count actually written by R43A.

## Count semantics

- `bound_media_count`: raw bound observation candidate count.
- `raw_bound_media_candidate_count`: explicit alias for the raw observation count.
- `deduped_bound_media_candidate_count`: unique bound media URL/class/path candidate count.
- `duplicate_bound_media_candidate_count`: raw bound candidates minus unique bound candidates.
- `ledger_media_item_count`: deduped media items on post records that flow to the ledger/media index.

This makes the live R43T summary safer as the baseline for R43U/R43V and avoids confusing
real-smoke cases where `bound_media_count` is larger than `media_index.json` rows.

## Boundary

No remote media downloads, browser profile reads, cookie/token extraction, hidden API scraping,
or challenge bypass is added.

## R43U0 live unbound-media clarification

A live Twitter/X account capture can validly produce visible media observations that cannot be
bound to any visible post in the current viewport. In live scope, that is not a blocker when
visible posts, date/post folders, screenshots, and the unbound media index are still written.

Fixture scope still requires explicit status-id/canonical-url/article-DOM bindings so regressions
in the proven R43T baseline are caught. Live scope now records zero bound media and nonzero
unbound media as a valid evidence state instead of reporting a fake failure.
