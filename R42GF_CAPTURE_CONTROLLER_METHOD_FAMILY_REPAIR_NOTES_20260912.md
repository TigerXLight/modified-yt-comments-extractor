# R42GF capture-controller method-family repair — 2026-09-12

## Purpose

Repair the downstream `capture_controller_test.py` failure exposed while closing out R42GF.

The R42GF-specific validator and the Twitter/X tests passed. The broader suite then reached an older controller contract:

```text
result.method_profile_family == "article_comments_manual_observation"
```

`source_adapters.py` was returning the MSN default method family as:

```text
article_comments_browser_and_local_import
```

This repair restores the controller-facing/default-profile family to:

```text
article_comments_manual_observation
```

## Boundary

This repair does not change the Twitter/X closeout route, does not perform network work, and does not mark any capture as executed.

It keeps:

- R42GF Twitter/X specialist closeout intact.
- MSN operational capture plans as model-only / approval-gated.
- `USER_REVIEW_REQUIRED` grabbed-source records.
- no live site fetch, browser automation, screenshot, download, archive submit, provider call, credential use, or CAPTCHA/rate-limit/access-control bypass.

## Files

- `source_adapters.py`
- `capture_controller_method_family_repair_r42gf_test.py`
