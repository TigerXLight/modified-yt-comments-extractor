# R42GB universal webpage media route validation

## Scope

R42GB is a validation-only patch after commit `c0f67b7` / R42GA. It proves the selected public webpage **Video & Audio → FILES** path is API3128/JDownloader-first where safe, while keeping direct/local handling for localhost fixtures.

## What this adds

- `webpage_video_api3128_route_validation_r42gb.py`
  - side-effect-free validator for the selected webpage media route
  - static route-order checks against `main.py`
  - sample route decisions for public direct files, stream manifests, embedded/player URLs and localhost fixtures
  - optional JSON + Markdown report writer
- `webpage_video_api3128_route_validation_r42gb_test.py`
  - asserts public file/stream/embed samples prefer API3128/JDownloader
  - asserts localhost stays unsupported for API3128 and remains on the direct/local path
  - asserts the selected-resource method in `main.py` performs API3128 checks/handoff before direct `urllib` fallback

## Boundary

This patch does not start JDownloader, download media, fetch a webpage, submit to an archive service, take screenshots, or touch CAPTCHA/access-control handling.

`shared_media_backend.py` is tracked in the project but was not included in the uploaded R42GB context ZIP, so this patch does not edit or import that file. It validates the API3128-first route through the already-present `webpage_video_api3128_route_r42fx.py` helper and static route-order checks.

## Expected report summary

```text
R42GB selected webpage media API3128/JDownloader route validation
Passed: true
Conclusion: R42GB PASS: selected public webpage media candidates are validated as API3128/JDownloader-first, while localhost/local fixtures remain on the direct/local path.
Side effects: no network fetch, no archive submission, no media download, no screenshot, no CAPTCHA/access bypass
```
