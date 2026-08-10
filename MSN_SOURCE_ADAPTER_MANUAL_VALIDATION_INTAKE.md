# MSN Source Adapter Manual Validation Intake

This intake records the final human check for a real MSN capture. It is not a scraper and does not run live capture automatically.

The intake covers:

- article title/body and publisher/source credit visibility
- Top/Newest comments and nested reply/profile export checks
- offline rendered HTML, WARC replay, and strict WACZ labelling
- media inventory/download or media status sidecars
- video/stream status recording
- source-role and primary-source-status review
- total package and final validation report presence

## Create a template

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe "T:\References\to go\Media\tools\Modified YouTube comment extractor\source_msn_adapter_manual_validation.py" template "%USERPROFILE%\Downloads\MSN_MANUAL_LIVE_VALIDATION_TEMPLATE.json" --source-url "https://www.msn.com/..." --capture-root "C:\Path\To\MSN\Capture\Folder"
```

Fill the JSON checks with `PASS`, `PARTIAL`, `FAIL`, or `NOT_CHECKED`, add evidence paths/notes, then render it:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe "T:\References\to go\Media\tools\Modified YouTube comment extractor\source_msn_adapter_manual_validation.py" result "%USERPROFILE%\Downloads\MSN_MANUAL_LIVE_VALIDATION_TEMPLATE.json" --output-dir "%USERPROFILE%\Downloads\MSN_MANUAL_LIVE_VALIDATION_RESULT"
```

## Source-chain warning

MSN, a republishing outlet such as The Independent, a visible credit such as Google Street View, an agency/family/authority statement, and the unknown original uploader/author must remain separate source-chain facts. Manual validation confirms whether that separation was checked; it does not automatically prove primary sourcing for every claim.
