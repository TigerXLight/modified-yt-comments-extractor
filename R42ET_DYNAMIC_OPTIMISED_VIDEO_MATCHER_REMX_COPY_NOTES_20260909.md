# R42ET — Dynamic Optimised video matcher + remux/copy conversion

Scope: File Converter only. Local FFmpeg/FFprobe only. No network, WebView2, archive.ph, browser, account, or adapter actions.

## User-corrected model

- Convert should mainly prefer remux/copy for video when no compression/target-size/handling changes require transcoding.
- The per-row `C` stays as Compression: it forces a compression/size-optimise pass.
- Simple presets are reduced to `Optimised` and `Speed`.
- `Optimised` is not a fixed CRF or fixed encoder. It is a metadata/capability matcher.
- Optional target file-size caps are allowed for upload limits such as Discord/Instagram forms.

## Backend

- Added fast ffprobe metadata extraction: duration, resolution, fps, source codec, audio codec, video bitrate, audio bitrate, container, and bits-per-pixel-frame.
- Added local encoder capability probe for hardware and software encoders.
- Added dynamic auto matcher for H.264, HEVC/H.265, VP9, and AV1.
- Added target-size bitrate mode when `target_file_size_mb` is set.
- Normal video Convert now emits `-c copy` / remux when no forced transcode is required.
- Compression or target-size mode invokes the dynamic matcher and records its selected encoder, mode, metadata, capability, and reason in the plan.

## UI

- Convert settings Simple: `Preset` and optional `Target size MB` only.
- Compression settings Simple: `Preset` and optional `Target size MB` only.
- Advanced keeps exact manual controls: image settings, audio bitrate/sample-rate/channel/speed/CUE, video encoder/manual CRF/max side/encoder speed/FPS.
- Removed old `Quality` / `Lower Size` simple preset wording and removed `File Size: Small / Medium / Max` slider.

## Important boundary

This patch ports the planning/matching logic into the Python desktop app. It does not vendor or execute the Android/Kotlin app source, and it does not add a real sample-encode benchmark yet. The next accuracy step should add a cached short sample benchmark to calibrate runtime and output-size estimates on the user's machine.
