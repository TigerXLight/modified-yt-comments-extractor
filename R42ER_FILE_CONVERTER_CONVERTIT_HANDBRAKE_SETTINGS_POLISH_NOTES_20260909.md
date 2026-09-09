# R42ER - File Converter Convertit/HandBrake settings polish

Purpose: address the remaining File Converter settings/UI issues after R42EQ.

What changed:

- `Optimised` is now a preset/dropdown concept, not a slider position.
- `Compression settings` Simple view uses `Preset` plus a `File Size` slider with `Small / Medium / Max`.
- `Compression settings` Advanced now actually switches to a different pane and exposes raw backend values.
- `Convert settings` Simple view now has practical preset-style conversion rows for Image, Video, and Audio.
- `Convert settings` Advanced is handling-only: bitrate, sample rate, channel control, playback speed, CUE split mode, metadata, web optimise, video encoder, video preset, and FPS.
- Audio sample rate is displayed as kHz labels such as `44.1 kHz`; backend receives Hz.
- Convertit-style audio reference concepts were ported into the backend: bitrate range, codec/output range, sample-rate range, channel control, playback-speed handling, AMR mono/16 kHz guard, and CUE split setting metadata.
- HandBrake-style video reference concepts were ported into settings: preset groups, CRF/RF-style quality, max-side downscale, frame-rate cap, encoder choice, and fast-start/web optimisation.
- File Converter held rows keep the parent/child fillbox indentation again.
- FILES gets blank-area drag/lasso selection: start dragging in empty FILES space and rows touched by the drag become selected.
- K and C icon assets are included from the supplied Icons8 zip files and remain label-style toggles to avoid rebuild/refresh button flashing.

Boundaries:

- This does not wholesale vendor HandBrake or the Android Convertit app into the Python app.
- It ports the relevant settings model and FFmpeg command-planning behaviour into the existing local converter backend.
- CUE track splitting is stored/exposed and passed in plan metadata; a full multi-output CUE splitting worker should be a later patch because it changes result cardinality.
- JS/browser compression repos remain external references for later WebView/browser-native compression work.
