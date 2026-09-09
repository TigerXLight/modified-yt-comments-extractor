# R42EQ File Converter preset and Convert settings polish

This patch is scoped to the File Converter UI/backend polish after R42EP.

## User-visible changes

- Restores the parent/child fill-box visual structure in the File Converter:
  - parent fill-box row is left aligned
  - held file fill-box rows are indented underneath it
- Enlarges File Converter held-row fill boxes.
- Keeps held-row K/C toggles as non-button labels so clicking them does not rebuild the row or show button refresh behaviour.
- Adds an ASR-style cog to the `Convert` button.
- Renames the compression window title to `Compression settings`.
- Moves the `Simple | Advanced` switch into the settings header row.
- Changes Simple compression labels to:
  - `Image quality`
  - `Video quality`
  - `Audio quality`
  - `Video size reduction`
- Adds a percentage slider for `Video size reduction`.
- Adds an `Optimised` preset for image, video, and audio.
- Raises audio choices beyond 192k in Advanced and in backend validation.
- Keeps the `Transcript Editor` label from R42EP.

## Source-reference boundary

The attached Convertit source was inspected as a reference for format/bitrate/sample-rate coverage and conversion architecture. This patch does not vendor or paste Convertit Android/Kotlin source into the Python app. It ports the relevant concepts into Python:

- expanded audio output choices
- expanded bitrate choices from 9k through 1024k
- sample-rate choices from source/8000 through 192000
- local FFmpeg command planning with metadata-preservation option

The JavaScript compression repos are still external references unless a later source-intake patch explicitly vendors selected files, keeps their license notices, and wires them into a runtime path.
