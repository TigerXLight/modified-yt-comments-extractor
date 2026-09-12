# R42GH Source Map Raw URL + Public Audio/Catch-up Repair Notes

Status target: `PASS_R42GH_SOURCE_MAP_RAW_URL_AUDIO_CATCHUP_REPAIR`

R42GH continues the R42GG universal source map/method registry. It is a map, sanitizer, evidence-contract, and report pass only.

## Implemented

- R42GG sanitizer now stores `extracted_url` and `normalized_url` as plain URL strings, not markdown wrappers.
- Tracking/share parameters such as `utm_*`, `s=20`, `fbclid`, `gclid`, `igsh`, and `si` are stripped where safe.
- `twitter.com` canonicalizes to `x.com` for universal route identity.
- Escaped/slashed URLs such as `https:\/\/x.com\/...` normalize correctly.
- Added `public_broadcast_catchup_audio` family for Global Player/LBC/commercial radio catch-up and public podcast-audio download routes.
- Added method metadata for the proven Global Player route:
  - backend `yt_dlp_python_module`
  - preferred invocation `py -m yt_dlp`
  - stale PATH executable avoidance
  - format probe requirement
  - native format `0`
  - native M4A preservation
  - info-json, description, and thumbnail sidecars
  - no conversion for preservation
- Added audio/catch-up export layout and evidence record shape.
- Added audio/catch-up review-string bridge fields.
- Added R42GH CLI/report marker and report check `sample_plan_urls_are_plain_not_markdown`.

## Boundaries

- No network fetch.
- No live browser launch.
- No media download.
- No yt-dlp execution.
- No extension execution.
- No CAPTCHA/security bypass.
- No credential/cookie/token harvesting.
- No source-role/counter/no-jump mutation.
- No review-window rewrite.

## Verification Environment Note

The `py -3.11` launcher in this Codex shell resolves to a WindowsApps Python stub and returns `Access is denied`. Verification was run with the installed Python 3.11 executable at `C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe`, using the command list from the R42GH handoff.
