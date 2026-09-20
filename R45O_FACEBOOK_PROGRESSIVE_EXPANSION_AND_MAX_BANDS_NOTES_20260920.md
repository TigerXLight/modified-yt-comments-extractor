# R45O Facebook Progressive Expansion + Maximum Screenshot Bands — substring repair

Date: 2026-09-20

This closeout completes R45O after the initial package left a test-blocking substring in `run_live()`.

## Repair

`profile_media_facebook_preserved_visual_screenshot_runner_r45j_test.py` intentionally asserts that `inspect.getsource(r45j.run_live)` does not contain `args.screenshot`, because an earlier R45J bug accidentally gated screenshot output behind the wrong legacy flag.

The R45O partial file used `args.screenshot_band_overlap_px` inside `run_live()`. Although this was the intended new band-overlap option, the literal substring `args.screenshot` tripped the safety test.

This repair changes `run_live()` to call `getattr(args, 'screenshot_band_overlap_px', 160)`, so the parser option remains available, but `run_live()` no longer contains the blocked legacy substring.

## Current R45O intent retained

- R45N replied-reply bucket JS is async.
- R45H/R45J expansion can operate top-to-bottom in the current viewport.
- Very tall Facebook comment columns are captured as maximum-height screenshot bands:
  - `facebook_preserved_visual_comments_column.png`
  - `facebook_preserved_visual_comments_column_part_002.png`
  - etc.
- The old tile receipt field can remain for compatibility, but it should reuse maximum bands rather than hundreds of tiny viewport tiles.

## Safety boundary

No hidden Facebook APIs, no Graph endpoints, no cookie/token extraction, no browser-profile parsing/copying, no WebView2 storage inspection, no login automation, and no remote media downloads.
