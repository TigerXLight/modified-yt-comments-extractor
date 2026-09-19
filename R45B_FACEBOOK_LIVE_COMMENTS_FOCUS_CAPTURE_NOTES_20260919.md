# R45B — Facebook live comments-only focus capture

R45B adds the missing live/intermediate Facebook capture layer above R45A.

## Purpose

R45A proved the static Print Edit WE-style text lane. R45B records and tests the
live method needed before static cleanup:

1. Open a logged-in Facebook post/permalink in Chromium or WebView2.
2. Apply CSS-only comments focus mode.
3. Keep the real Facebook comments DOM live and clickable.
4. Operator expands `View replies`, `View more`, and `See more` controls.
5. Capture screenshot, raw DOM, visible innerText/textContent.
6. Parse loaded text into JSON/NDJSON/Markdown.
7. Compare against a reference `text.txt` dump when supplied.

## Key rule

Use **CSS hiding**, not destructive delete, while expanding comments. Print-clean
or delete-without-float is allowed only after all required comments/replies are
loaded.

## Safety rules

R45B does not use hidden Facebook APIs, does not automate login, does not extract
cookies/tokens, and does not read/copy/parse browser profile files or WebView2
storage.

## Comparison with text.txt

```cmd
python profile_media_facebook_live_comments_focus_capture_r45b.py --compare-text --candidate-text C:\path\to\candidate.txt --reference-text C:\path\to\text.txt
```

For a live capture after the operator expands the page:

```cmd
python profile_media_facebook_live_comments_focus_capture_r45b.py --live --target-url "https://www.facebook.com/permalink.php?..." --chromium-executable "C:\path\to\chrome.exe" --user-data-dir "C:\path\to\facebook_profile" --reference-text "C:\path\to\text.txt"
```

The comparison reports filtered-line coverage plus sentinel checks for known
reference comments.
