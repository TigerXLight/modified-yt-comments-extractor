# R42GF capture-controller media-selection repair — 2026-09-12

## Purpose

Repair the second downstream `capture_controller_test.py` compatibility failure exposed after the R42GF Twitter/X closeout patch and the MSN method-family repair.

The first repair restored the MSN method family expected by the operational controller. The next controller assertion failed in the media/mux planning test because the test still assumed MSN source rows inject two fake fixture video/audio resources:

```text
selected_ids = tuple(item.resource_id for item in row.video_audio_resources[:2])
```

The current source-row contract says MSN no longer injects fake fixture media. Media discovery is user-triggered, and the controller can still declare a plan when explicit selected media resource IDs are supplied.

## Change

`capture_controller_test.py` now asserts the current MSN row contract:

```text
row.video_audio_resources == ()
```

Then it supplies two explicit user-selected public media candidate IDs to verify the existing media inventory, two media file declarations, and mux component declaration remain unchanged and plan-only.

## Boundary

This patch does not change runtime capture behavior. It does not perform network fetches, browser automation, screenshots, downloads, archive calls, provider calls, credential use, or CAPTCHA/rate-limit/access-control bypass.

It preserves the R42GF Twitter/X closeout and the controller's model-only / approval-gated media planning behavior.

## Files

- `capture_controller_test.py`
- `capture_controller_media_selection_repair_r42gf_test.py`
