# Rendered Citation Media Intake V77E

Status: IMPLEMENTED, CLI_ONLY, TESTED, local/offline manifest writer.

V77E bridges V77D rendered-citation/source-preservation metadata into Profile/Media source-unit media inventory. It records existing local files or blocked/source-reference-only records without mutating source folders and without copying media into HOME.

## What V77E Does

- Accepts an already existing local file supplied by the user.
- Records file name, extension, MIME-ish type from stdlib `mimetypes`, size, and SHA-256.
- Records source URL, page URL, media/reference URL, capture kind, capture method, media position, source-unit path, and user-declared purpose.
- Embeds V77D-compatible rendered citation metadata.
- Preserves human-mediated access/challenge fields.
- Records blocked capture placeholder records when no local file exists.
- Infers a source-unit attachment scope from the supplied path.
- Writes only a JSON manifest, and only with an explicit confirmation token.

## What V77E Does Not Do

- No browser launch.
- No network request.
- No URL fetch.
- No media download.
- No screen recording.
- No file copy into HOME/database folders.
- No DRM/CDM patching, decryption key extraction, licence-server impersonation, HDCP defeat, or hidden protected-stream extraction.
- No self-acting CAPTCHA solving, solver service, fake-human challenge automation, proxy/evasion, or forced rate-limit bypass.
- No credential automation.
- No X/Twitter write actions.

## Manifest Schema

Schema version:

`rendered-citation-media-intake-v77e`

Important fields:

- `source_url`
- `page_url`
- `media_url`
- `source_unit_path`
- `user_declared_purpose`
- `capture_kind`
- `capture_method`
- `media_position_start`
- `media_position_end`
- `local_file_path`
- `local_file_name`
- `local_file_extension`
- `local_file_mime_type`
- `local_file_size`
- `local_file_sha256`
- `local_file_present`
- `local_file_role`
- `source_unit_attachment`
- `rendered_citation_metadata`
- `human_mediated_access`
- `blocked_capture`
- `safety_flags`

## Local File Roles

- `screenshot`
- `still_frame`
- `video_excerpt`
- `audio_excerpt`
- `subtitle_caption`
- `transcript`
- `livestream_excerpt`
- `source_reference_only`
- `blocked_capture_placeholder`
- `review_required`

## Source-Unit Attachment Scopes

The module preserves the supplied `source_unit_path` and infers:

- `article_source_unit`
- `social_video_source_unit`
- `twitter_x_source_unit`
- `internal_media`
- `reference_extant`
- `review_required`

This is a logical attachment only. V77E does not copy or move files.

## Write Gate

Writing output JSON requires:

`WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E`

## CLI Example

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_rendered_citation_media_intake_cli_v77e.py --source-url https://example.com/source --page-url https://example.com/source --source-unit-path "Sources\Social Media\Online\X\example" --purpose source_preservation --capture-kind still_frame --capture-method local_file_preservation --local-file "%TEMP%\ytce_v77e_fixture.txt" --local-file-role source_reference_only --output-json "%TEMP%\ytce_rendered_citation_media_intake_v77e.json" --confirm-write WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E --print-text
```

Expected markers:

- `schema_version: rendered-citation-media-intake-v77e`
- `local_file_present: True`
- `local_file_size: nonzero`
- `local_file_sha256: nonblank`
- `local_file_role: source_reference_only`
- `source_unit_attachment.attached_to_source_unit: True`
- `human_mediated_access.program_solved_challenge: False`
- `safety_flags.browser_launch_performed: False`
- `safety_flags.web_download_performed: False`
- `safety_flags.media_download_performed: False`
- `safety_flags.recording_performed: False`
- `safety_flags.drm_circumvention_performed: False`
- `safety_flags.proxy_or_evasion_performed: False`
