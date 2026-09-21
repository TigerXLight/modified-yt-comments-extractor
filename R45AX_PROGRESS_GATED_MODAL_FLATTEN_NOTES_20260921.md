# R45AX progress-gated modal flatten closeout

Purpose: finish the Facebook comments capture without accepting an incomplete run.

R45AW proved the separated max-band capture path works, but its success gate was too weak: it could pass after a visible-control audit even while Facebook's own modal progress had not reached the total. R45AX adds a progress gate such as `657 of 715` / `696 of 715` / `715 of 715`.

Rules:
- Visible-page-only expansion in the operator-controlled signed-in Chromium profile.
- No hidden Facebook APIs, Graph endpoints, cookies, tokens, browser profile parsing/copying, or WebView2 storage inspection.
- Open the target post, lock to the expected story_fbid, find the active comments scroller.
- Click the first safe visible expansion label in order, then rescan the same viewport.
- Continue downwards as comments load.
- Refuse final screenshots if a Facebook progress marker exists and current < total.
- Flatten the comments modal into a comments-only page with no internal scrollbox, then capture maximum-height bands with default 30000px band height.

Expected live success markers:
- `R45AX_PROGRESS_GATED_START`
- repeated `R45AX_SCAN`, `R45AX_CLICK`, `R45AX_SCROLL_DOWN`
- if incomplete: `R45AX_PROGRESS_GATE_NOT_SATISFIED` and eventually `R45AX_BLOCKED_INCOMPLETE_EXPANSION`
- if complete: `R45AX_EXPANSION_COMPLETE`, `R45AX_FLATTEN_COMMENTS_ONLY`, `R45AX_FINAL_SUMMARY`

Output ZIP:
- `r45ax_comments_only_max_bands.zip`

Do not trust a screenshot if `R45AX_BLOCKED_INCOMPLETE_EXPANSION` appears.
