# R42GA source_resource_state news_website repair

This supersedes the zero-byte/invalid R42FZ ZIP in the current ChatGPT sandbox.

Current live state from the user:

- R42FY repair applied.
- R42FX API3128/JDownloader files are present.
- `py_compile`, `webpage_video_api3128_route_r42fx_test.py`, `profile_media_universal_source_capability_matrix_r42fx_test.py`, and `source_adapters_test.py` passed.
- `source_resource_state_test.py` failed with `NameError: name 'title' is not defined` in `_canonicalize_for_adapter()`.

Fix:

- Remove the accidentally inserted `news_website` row-state branch from `_canonicalize_for_adapter()`.
- Leave `_canonicalize_for_adapter()` with only `canonical = adapter.normalize_url(url)` for `news_website`.
- Ensure the Metro/news status branch exists only in `build_source_resource_row()`.
- Add a guard that fails immediately if the canonicalizer still contains row-only names.

No network fetch, archive submission, CAPTCHA/access-control bypass, media download, screenshot, `git clean`, or deletion of project data is performed.
