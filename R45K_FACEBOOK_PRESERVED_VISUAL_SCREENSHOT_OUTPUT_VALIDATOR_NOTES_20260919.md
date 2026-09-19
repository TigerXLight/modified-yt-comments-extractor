# R45K Facebook preserved visual screenshot output validator

R45K is a local artifact-only closeout layer for R45J.

R45J fixed the preserved visual blank-page problem by keeping the live Facebook-rendered comments DOM in place instead of cloning/replacing `document.body`. R45K does not perform another capture. It validates the output from an existing R45J run so the blank-page failure cannot be missed when text exports exist but screenshots render white.

R45K checks:

- an R45J receipt JSON exists;
- preserved visual full-page and/or tiled screenshot paths are recorded;
- screenshot files exist and are non-empty;
- screenshots decode as local images;
- screenshots have valid dimensions;
- screenshots are not effectively blank/near-white using a conservative sampled non-near-white pixel ratio;
- visible text export exists and is non-empty;
- the R45J receipt confirms no hidden Facebook APIs, no login automation, no cookie/token extraction, no browser-profile reading/copying/parsing, no WebView2 storage inspection, and no remote media downloads.

Safety contract:

- R45K does not launch a browser.
- R45K does not navigate or perform network actions.
- R45K does not click page controls.
- R45K does not read, copy, or parse browser profile files.
- R45K does not inspect cookies/tokens/WebView2 storage.
- R45K does not use hidden Facebook APIs or Graph endpoints.
- R45K does not download remote media.

Example after a live/manual R45J run:

```bat
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_facebook_preserved_visual_screenshot_output_validator_r45k.py --output-dir profile_media_live_captures/r45j_facebook_preserved_visual_screenshot_runner
```

Example with an explicit receipt:

```bat
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_facebook_preserved_visual_screenshot_output_validator_r45k.py --receipt "profile_media_live_captures\r45j_facebook_preserved_visual_screenshot_runner\facebook_preserved_visual_screenshot_runner_YYYYMMDDTHHMMSSZ\r45j_facebook_preserved_visual_screenshot_runner_receipt.json"
```

Expected marker:

`YTCE_R45K_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_OUTPUT_VALIDATOR`

Expected pass status:

`PASS_R45K_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_OUTPUT_VALIDATOR`
