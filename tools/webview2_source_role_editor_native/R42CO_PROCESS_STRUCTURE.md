# R42CP archive material chain wiring

R42CP moves the archive.ph source-row material path out of the generic Playwright-only route.

Observed failure before R42CP:

```text
GO -> Webpage on archive.ph/6mr3C
-> Generic website live capture did not complete
-> browser_status=FAILED
-> no fresh archive.ph/6Mr3C live-capture directory
-> no source-role overlay/roleplan artifacts
```

R42CP target:

```text
Source URL row 03 archive.ph/6mr3C
-> source-material chain runs first
-> direct archive/mirror material probe
-> existing Edge/CDP link-sourcing route is called from GO/Webpage, not only from the inspection/details path
-> article text/html artifacts are written under profile_media_live_captures/r42cp_archive_source_material
-> artifacts are added to FILES for source-role review
-> generic Playwright route is only fallback
```

This is about wiring the browser/material access path into the batch source-role pipeline. The edit window remains optional inspection; source rows must be processed by the app.
