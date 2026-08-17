# V77E Command Index

Patch: V77E - rendered citation local media intake and source-unit preservation bridge.

## Safety

These commands are offline/local. They do not launch a browser, use the network, fetch URLs, download media, crawl, record the screen, automate credentials, solve CAPTCHA, bypass DRM, use proxy/evasion, force rate limits, or perform X/Twitter write actions.

## Compile

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe -m py_compile rendered_citation_media_intake_v77e.py rendered_citation_media_intake_v77e_test.py tools\run_rendered_citation_media_intake_cli_v77e.py rendered_citation_recording_metadata_v77d.py rendered_citation_recording_metadata_v77d_test.py
```

## Tests

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe rendered_citation_media_intake_v77e_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe rendered_citation_recording_metadata_v77d_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe external_reference_absorption_v77d_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_live_output_closeout_v77c_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_nested_source_units_v77b_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_screenshot_preservation_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_profile_media_provenance_test.py
```

## CLI Smoke

Create a small local fixture:

```cmd
echo V77E local source-reference fixture>"%TEMP%\ytce_v77e_fixture.txt"
```

Run the intake:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_rendered_citation_media_intake_cli_v77e.py --source-url https://example.com/source --page-url https://example.com/source --source-unit-path "Sources\Social Media\Online\X\example" --purpose source_preservation --capture-kind still_frame --capture-method local_file_preservation --local-file "%TEMP%\ytce_v77e_fixture.txt" --local-file-role source_reference_only --output-json "%TEMP%\ytce_rendered_citation_media_intake_v77e.json" --confirm-write WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E --print-text
```

## Hygiene

```cmd
git diff --check
git status --short
```

## Suggested Commit

Do not add external reference folders.

```cmd
git add rendered_citation_media_intake_v77e.py rendered_citation_media_intake_v77e_test.py tools\run_rendered_citation_media_intake_cli_v77e.py RENDERED_CITATION_MEDIA_INTAKE_V77E.md V77E_COMMAND_INDEX.md testdata\rendered_citation_media_intake_v77e_acceptance_matrix.json && git commit -m "Add rendered citation media intake bridge"
```
