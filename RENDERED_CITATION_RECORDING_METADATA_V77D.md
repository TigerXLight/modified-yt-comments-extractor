# Rendered Citation Recording Metadata V77D

Status: IMPLEMENTED, CLI_ONLY, TESTED, metadata-only.

V77D adds a safe local manifest for rendered citation/source-preservation records. It is designed for situations where a human reviewer has a visible browser/window/source and needs to bind a local preservation artifact or blocked-capture state to a source URL, media position, purpose, and Profile/Media source unit.

## What It Does

The module `rendered_citation_recording_metadata_v77d.py` records:

- `source_url`
- `page_url`
- `media_url`
- `capture_kind`
- `capture_method`
- `user_declared_purpose`
- timestamps and media-position fields
- optional local file path, size, and SHA-256
- source unit path
- blocked capture state
- human-mediated access/challenge state
- safety flags

The CLI is `tools/run_rendered_citation_recording_metadata_cli_v77d.py`.

## Capture Kinds

- `still_frame`
- `window_recording`
- `region_recording`
- `bounded_video_excerpt`
- `bounded_audio_excerpt`
- `subtitle_caption_capture`
- `livestream_excerpt`
- `blocked_capture_state`

## Capture Methods

- `ordinary_browser_visible_capture`
- `ordinary_windows_screen_capture`
- `browser_print_or_save`
- `local_file_preservation`
- `source_reference_only`

## User-Declared Purposes

- `quotation`
- `criticism`
- `review`
- `news_reporting`
- `research`
- `source_preservation`
- `other_review_required`

## Blocked Reasons

- `black_frame`
- `muted_audio`
- `drm_or_platform_restriction`
- `login_required`
- `access_boundary`
- `captcha_or_challenge_required`
- `rate_limit_or_cooldown`
- `unknown`

## Human-Mediated Challenge Boundary

Allowed:

- The program may record that a normal visible challenge/access step was required.
- The program may record that the human user completed that challenge.
- The manifest may record `completion_recorded: true`.

Not allowed:

- Program-solved CAPTCHA.
- Solver services.
- Anti-detection tricks.
- Proxy/evasion behavior.
- Forced rate-limit bypass.

The manifest hard-codes:

- `program_solved_challenge: false`
- `solver_service_used: false`
- `anti_detection_used: false`
- `captcha_solver_used: false`
- `proxy_or_evasion_performed: false`
- `forced_rate_limit_bypass_performed: false`

## Write Gate

Writing JSON requires:

`WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D`

Without the token, the CLI prints a confirmation-required error and does not write the JSON file.

## Example

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_rendered_citation_recording_metadata_cli_v77d.py --source-url https://example.com/source --page-url https://example.com/source --capture-kind blocked_capture_state --capture-method ordinary_browser_visible_capture --purpose source_preservation --capture-blocked --blocked-reason captcha_or_challenge_required --human-mediated-access-required --human-mediated-access-completed-by-user --output-json "%TEMP%\ytce_rendered_citation_recording_v77d.json" --confirm-write WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D --print-text
```

Expected markers:

- `schema_version: rendered-citation-recording-metadata-v77d`
- `capture_kind: blocked_capture_state`
- `capture_method: ordinary_browser_visible_capture`
- `user_declared_purpose: source_preservation`
- `capture_blocked: True`
- `blocked_reason: captcha_or_challenge_required`
- `human_mediated_access.required: True`
- `human_mediated_access.completed_by_user: True`
- `human_mediated_access.program_solved_challenge: False`
- `human_mediated_access.solver_service_used: False`
- `human_mediated_access.anti_detection_used: False`
- `safety_flags.drm_circumvention_performed: False`
- `safety_flags.proxy_or_evasion_performed: False`
- `safety_flags.forced_rate_limit_bypass_performed: False`

## Not Implemented In V77D

- Actual screen recording.
- Browser automation.
- Browser launch.
- Web downloads.
- Media downloads.
- OCR.
- DRM/protected stream extraction.
- Twitter/X live capture.
- Automatic source-role final classification.
