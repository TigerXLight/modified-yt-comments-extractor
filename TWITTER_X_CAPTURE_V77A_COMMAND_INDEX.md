# Twitter/X Capture V77A Command Index

## Validation Commands

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe -m py_compile twitter_capture_current_capabilities_v77a.py twitter_capture_screenshot_preservation.py twitter_capture_screenshot_preservation_test.py twitter_capture_profile_media_provenance.py twitter_capture_profile_media_provenance_test.py tools\run_twitter_capture_screenshot_preservation_cli_v77a.py
```

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_screenshot_preservation_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_profile_media_provenance_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_twitter_capture_screenshot_preservation_cli_v77a.py --print-text
git diff --check
git diff --stat
git status --short
```

## Offline Proof CLI

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_twitter_capture_screenshot_preservation_cli_v77a.py --print-text
```

The CLI is read-only and uses `testdata\twitter_capture_v77a_fixture`. It does not launch a browser, hit X/Twitter, download media, use the official X API, read credentials, or scan HOME folders.

## Suggested Commit Command

```cmd
git add twitter_capture_current_capabilities_v77a.py twitter_capture_screenshot_preservation.py twitter_capture_screenshot_preservation_test.py twitter_capture_profile_media_provenance.py twitter_capture_profile_media_provenance_test.py tools\run_twitter_capture_screenshot_preservation_cli_v77a.py testdata\twitter_capture_v77a_fixture\rendered_dom_snapshot.html testdata\twitter_capture_v77a_fixture\screenshots\viewport_capture.txt testdata\twitter_capture_v77a_fixture\screenshots\full_page_capture.txt testdata\twitter_capture_v77a_acceptance_matrix.json TWITTER_X_CAPTURE_V77A_CURRENT_STATUS.md TWITTER_X_CAPTURE_V77A_SCREENSHOT_PRESERVATION.md TWITTER_X_CAPTURE_V77A_PROFILE_MEDIA_BRIDGE.md TWITTER_X_CAPTURE_V77A_COMMAND_INDEX.md && git commit -m "Add Twitter capture screenshot preservation proof"
```
