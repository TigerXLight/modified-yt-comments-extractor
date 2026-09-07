# R42EH File Converter Auto-Detect + Reference-Backed Implementation

Scope:
- Builds on R42EG File Converter scaffold.
- Keeps the File Converter panel under the progress bar beside Transcript/Text Editor.
- Keeps FILES row K/kappa keep-original semantics.
- Adds layered auto-detection: extension, mimetype, ffprobe fallback, text sniff, UNKNOWN warning.
- Adds Auto target preset: text -> html, image -> webp, audio -> mp3, video -> mp4.
- Keeps conversion local-only with Python text conversion and local ffmpeg/ffprobe media conversion.
- Replaces pytest-dependent smoke with direct stdlib test execution.

Safety:
- No network.
- No archive.ph.
- No browser/WebView2 required for smoke/probe.
- No account/channel/device adapters.
- K disabled deletes the original only after successful output exists and the UI confirmation path has approved the destructive run.
- Failed conversion keeps original files.

Acceptance commands:

```cmd
cd /d "T:\References\to go\Media\tools\Modified YouTube comment extractor" && tools\webview2_source_role_editor_native\smoke_r42eh_file_converter_auto_detect.cmd
cd /d "T:\References\to go\Media\tools\Modified YouTube comment extractor" && tools\webview2_source_role_editor_native\probe_r42eh_file_converter_auto_detect_no_gui.cmd
cd /d "T:\References\to go\Media\tools\Modified YouTube comment extractor" && tools\webview2_source_role_editor_native\make_r42eh_file_converter_auto_detect_debug_upload_zip.cmd
```
