# Twitter/X Capture V77C Command Index

## Validation Commands

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe -m py_compile twitter_capture_live_output_closeout_v77c.py twitter_capture_live_output_closeout_v77c_test.py tools\run_twitter_capture_live_output_closeout_cli_v77c.py twitter_capture_screenshot_preservation.py twitter_capture_profile_media_provenance.py twitter_capture_profile_media_provenance_test.py
```

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_screenshot_preservation_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_profile_media_provenance_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe twitter_capture_live_output_closeout_v77c_test.py
```

## Real Local Output Closeout

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_twitter_capture_live_output_closeout_cli_v77c.py --output-root "%TEMP%\ytce_twitter_v77b_manual_probe" --source-url https://x.com/examaddaorg --profile-tab replies --output-json "%TEMP%\ytce_twitter_v77c_live_output_closeout.json" --profile-media-records-jsonl "%TEMP%\ytce_twitter_v77c_profile_media_records.jsonl" --confirm-write WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C --print-text
```

This command is offline/read-only with respect to Twitter/X. It only reads local output files and writes closeout JSON/JSONL when the confirmation token is supplied.

## Write Confirmation Token

```text
WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C
```

Without the exact token, `--output-json` and `--profile-media-records-jsonl` are blocked.

## Suggested Commit Command

```cmd
git add twitter_capture_live_output_closeout_v77c.py twitter_capture_live_output_closeout_v77c_test.py tools\run_twitter_capture_live_output_closeout_cli_v77c.py TWITTER_X_CAPTURE_V77C_LIVE_OUTPUT_CLOSEOUT.md TWITTER_X_CAPTURE_V77C_COMMAND_INDEX.md testdata\twitter_capture_v77c_acceptance_matrix.json && git commit -m "Add Twitter live output closeout bridge"
```
