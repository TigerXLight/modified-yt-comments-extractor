# R42GD Generic Article/Webpage Lane Validation

R42GD adds a side-effect-free validation layer for the generic article/webpage route that sits after R42GC's source-family matrix.

## Scope

R42GD validates that ordinary public article URLs belong to the generic_article lane while platform-shaped sources stay on specialist routes.

Covered as generic article samples:

- Metro-style ordinary public article URL.
- Telegraph-style ordinary public article URL.
- BBC News-style ordinary public article URL.
- Unknown ordinary public webpage/article URL.

Excluded from generic_article:

- BBC Sounds/programme audio.
- Twitter/X posts/profiles/threads.
- Instagram public visual/social URLs.
- YouTube.
- Spotify podcast episode/show and Spotify music/non-podcast URLs.
- Direct public media candidates.
- Wayback and archive.today/archive.ph captures.

## Evidence boundary

The validation intentionally exercises only supplied offline HTML parsing. It does not fetch a live page or perform browser work.

Fields marked tested_true by R42GD:

- title
- byline
- published date
- canonical URL
- article text from supplied HTML
- image references recorded from supplied HTML
- outbound links recorded from supplied HTML

Fields deliberately not marked tested_true:

- screenshots
- WARC/WACZ
- archive lookup/import
- source-role material counter promotion
- comments

Those remain receipt-gated until an actual screenshot/WARC/archive/material replay/comments capture path is run and recorded.

## Safety boundary

R42GD performs no network fetch, no media download, no screenshot, no archive submission, no provider/API call, no account/session use, and no CAPTCHA/access-control bypass.

## Files

- `profile_media_generic_article_lane_validation_r42gd.py`
- `profile_media_generic_article_lane_validation_r42gd_test.py`

## Expected command

```cmd
py -3.11 profile_media_generic_article_lane_validation_r42gd.py --source-root . --output-root "profile_media_live_captures\r42gd_generic_article_lane" --url "https://example.com/2026/09/12/ordinary-public-article"
```

Expected headline:

```text
R42GD generic article/webpage lane validation
Passed: true
```

## Relationship to R42GB/R42GC

R42GB proved selected public webpage media candidates are API3128/JDownloader-first.

R42GC formalised the universal source adapter family matrix.

R42GD now closes the generic_article validation boundary without overclaiming screenshots, archives, comments, or source-role material counters.
