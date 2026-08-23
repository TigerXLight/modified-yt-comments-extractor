# Profile/Media Database V82A Source Package Preview

V82A starts the real Database polish by adding a safe bridge from source-row / FILES
artifacts into the existing Profile/Media Database import workbench.

## What this adds

- `profile_media_source_package_preview.py`
- `profile_media_source_package_preview_test.py`

The builder creates a reviewable Profile/Media batch JSON payload from:

- a source URL/title
- selected/captured artifacts such as video, image, article text, screenshot,
  transcript, or archive receipt metadata

The generated JSON is compatible with the existing Database Import flow because it
uses the existing case-batch payload shape:

```text
database_root
case_title
sources[]
profiles[]
```

No profiles are inferred in V82A.

## Safety behaviour

The preview builder does not:

- scan folders
- create folders unless explicitly writing the preview JSON path
- copy files
- download media
- download webpages
- perform screenshots
- call archive providers
- classify sources as final
- infer sensitive identifiers

The optional JSON write helper is gated by this exact phrase:

```text
WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW
```

The existing Save-to-HOME workflow remains separately gated by its own confirmation
phrase.

## Intended next step

After this module is stable, the GUI can add a small "Build DB import" action that
collects the current source row plus selected FILES/temp artifacts and writes a
reviewable import JSON for the Database Import button.
