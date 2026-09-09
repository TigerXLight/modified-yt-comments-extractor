# R42EP — File Converter compression button/settings polish

This patch tightens the File Converter compression workflow after the R42EO live review.

## User-facing fixes

- Replaces the separate small File Converter cog with the same Local ASR / Online ASR shared cog-button control:
  - main button text: `Compression`
  - cog overlay opens settings
  - main button toggles C/compression for selected held rows
- Changes the compression settings window to open in `Simple` mode first:
  - Image quality: Low / Medium / High slider
  - Video compression: Light / Medium / Strong slider
  - Audio compression: Small / Medium / High slider
  - Advanced keeps raw fields for quality, max pixels, CRF, max pixels, suffix, and bitrate.
- Renames `Keep all originals for this run` to `Keep all original files`.
- Renames `Transcript` to `Transcript Editor` to match `Text Editor`.
- Removes the noisy selected-count status update; the held-files master fillbox count is the selection indicator.
- Enlarges the held-row fillboxes and uses the unused left-side space in the held-files scroll area.
- Removes the per-row metadata line such as `video/extension default -> .mp4`; the row now prioritises filename, target dropdown, K, and C.
- Keeps the File Converter drop placeholder visible only while the held list is empty or while an active drag hover is happening.
- Removes the checkbox glyph from the drag ghost; drag feedback shows only the file name or file count.
- Strengthens cleanup for old generated `Converted:` folder/group state so converted outputs remain flat at FILES root.

## Reference-code status

The downloaded compression repos are reference material for the next engine-intake workstream. R42EP does not vendor or embed their JavaScript/WASM sources into the Python desktop app. That is intentional for this patch because runtime wiring, attribution, and license boundaries should be handled in a separate source-intake patch.

The relevant local reference map is:

- `compressorjs` — MIT, image-compression option model such as quality and max dimensions.
- `UPNG.js` — MIT, PNG compression reference.
- `mediabunny` — MPL-2.0, video/audio WebCodecs-oriented reference.
- `audiojs/encode` — MIT, audio encoder reference.
- `compress-pro` — MIT, full compressor workflow reference.

R42EP copies the established in-project UI logic where applicable: the Local/Online ASR cog control and the Review DB fillbox selection structure. It keeps compression execution on the existing local converter backend for now.

## Safety scope

No WebView2/archive.ph/network capture path is started by this patch. The converter remains local-only.
