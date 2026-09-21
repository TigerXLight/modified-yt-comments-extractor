# R45AH legacy 2026-09-19 Facebook expansion runner

This adds a separate legacy runner instead of continuing to patch the current R45J
file.

Why:
- The current R45V-R45AG path still visibly loops/scans and can leave expansion
  controls behind.
- The user supplied the older files from the session where expansion was working.
- This patch preserves the current branch state, but adds a legacy runner based
  on the uploaded 2026-09-19 R45H/R45J files.

Added files:
- `profile_media_facebook_bounded_modal_capture_runner_r45h_legacy_20260919.py`
- `profile_media_facebook_preserved_visual_screenshot_runner_r45j_legacy_20260919.py`

The legacy J runner imports the legacy H runner so it does not use the newer
R45V/R45AF/R45AG expansion path.

Safety contract remains unchanged:
- visible Facebook page expansion only
- no hidden Facebook APIs
- no cookies/tokens/profile parsing
- no WebView2 storage inspection
- no login automation
