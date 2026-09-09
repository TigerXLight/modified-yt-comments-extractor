# R42EU - Scrollable advanced tabs and compression target resolution settings

## Purpose

Repair the live converter/compression settings UX after R42ET:

- The cog/windows now launch; this patch addresses cramped/hidden content rather than the prior launch crash.
- Convert settings and Compression settings use scrollable bodies so long Advanced sections can be reached.
- Advanced settings are split into Image / Video / Audio tabs.
- Compression Simple keeps only Optimised / Speed and optional target-size, then adds simple target resolution dropdowns for Image and Video.
- Convert settings deliberately does not add target resolution in Simple mode; conversion should mainly remux/copy unless the requested format or handling requires re-encode.

## Behaviour

Compression Simple:

- Preset: Optimised | Speed
- Target size MB: optional cap for upload limits
- Image resolution: auto/source/720p/1080p/1440p/4K
- Video resolution: auto/source/480p/720p/1080p/1440p/4K

Compression Advanced:

- Image tab: image quality, max side, suffix, WebP method, PNG compression, JPG subsampling
- Video tab: encoder, manual CRF/RF, max side, encoder speed, frame rate
- Audio tab: bitrate, sample rate, channel control, playback speed

Convert Advanced:

- Image / Video / Audio tabs for handling settings and format defaults.
- Simple Convert remains Optimised | Speed + optional target-size cap.

## Notes

This patch does not remove the C icon. C remains Compression / force size-optimise.
R42ET dynamic metadata/capability matcher logic is retained.
