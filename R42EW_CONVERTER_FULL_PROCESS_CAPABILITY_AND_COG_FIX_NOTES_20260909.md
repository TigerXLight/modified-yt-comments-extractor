# R42EW converter full-process capability and cog fix

- Replaces the File Converter action cog overlay with a sibling CTkButton so it is visible before hover.
- Keeps Convert mainly remux/copy unless C compression, target-size, or explicit handling forces a transcode.
- Expands encoder capability recognition to include Windows Media Foundation encoders plus SVT/libaom/rav1e AV1 variants.
- Adds a no-network local full-process audit covering compile/import, text/image/audio conversion, video plan examples, system RAM/GPU probes, FFmpeg encoder reporting, and optional synthetic encoder benchmarks.
- Does not start the app, WebView2, archive.ph, or any network action during smoke/audit.
