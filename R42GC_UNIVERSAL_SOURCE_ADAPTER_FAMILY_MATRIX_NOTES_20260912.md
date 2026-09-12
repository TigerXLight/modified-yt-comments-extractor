# R42GC Universal Source Adapter Family Matrix

R42GC adds a side-effect-free source-family capability router. It does not fetch,
download, screenshot, submit archives, call providers, use accounts, or bypass
CAPTCHA/access controls.

## Purpose

R42FX/R42GA/R42GB closed useful slices:

- R42FX/R42GA: deep API3128/JDownloader media route plus Metro archive/capability scan and row-placement repair.
- R42GB: validation that selected public webpage media candidates are API3128/JDownloader-first while local fixtures stay direct/local.

R42GC does **not** claim every website is fully handled. It records the architecture
boundary the project needs:

```text
generic core + specialist adapters
```

The generic core covers ordinary public articles/webpages and generic media
candidate planning. Specialist adapters remain required for platform-shaped
sources such as BBC Sounds, podcasts, YouTube, Twitter/X, Instagram, and archive
services.

## Families recorded

```text
generic_article
generic_webpage_media
bbc_sounds
podcast_rss
apple_podcasts
spotify_podcast
youtube
twitter_x
instagram
archive_wayback
archive_today
local_warc_archive
```

## Important boundaries

- BBC Sounds uses the proven source-specific route: yt-dlp bestaudio to original
  asset, then ffmpeg audio-copy to M4A. This is not a global yt-dlp replacement.
- Spotify support is podcasts only. Spotify track/album/playlist music URLs are
  classified as unsupported/non-downloadable by this adapter family.
- Twitter/X remains `baseline_exists_not_closed`.
- Instagram remains `specialist_required`.
- Comments remain `not_tested` unless a site-specific comments path is actually
  exercised.
- Archive source material still needs replay proof before archive.ph/Wayback
  material can be marked green for source-role counters.

## Files

```text
profile_media_source_family_matrix_r42gc.py
profile_media_source_family_matrix_r42gc_test.py
```

## Validation command

```cmd
py -3.11 profile_media_source_family_matrix_r42gc_test.py
py -3.11 profile_media_source_family_matrix_r42gc.py --source-root . --output-root "profile_media_live_captures\r42gc_source_family_matrix"
```

## R42GC CLI append repair

The command-line `--url` argument now uses `default=None` and iterates over
`args.url or ()`. This prevents argparse `action=append` from trying to append
into an immutable tuple when multiple `--url` arguments are supplied. The test
suite now exercises repeated `--url` CLI usage and confirms that JSON/Markdown
report files are written without network/media/archive side effects.
