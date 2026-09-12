# R42GF session-files transcript panel guard repair

This repair is a narrow follow-up to the R42GF closeout test run.

## Problem

`session_files_test.py` exercises `App.__new__(App)` without constructing a real Tk root.
The transcript import path calls `_show_transcript_panel()`. The previous implementation used
`hasattr(self, "transcript_card")`, which can invoke Tkinter/CustomTkinter `__getattr__` and recurse
when the stub instance has no `tk` attribute.

## Change

The transcript panel and transcript drop-highlight helpers now consult `self.__dict__` for optional
widgets instead of probing Tk attributes. This preserves the real UI behaviour while making the
headless/session-file tests safe.

## Boundaries

- No Twitter/X route changes.
- No source-family matrix changes.
- No network, browser, API, screenshot, OCR, archive, media download, or evidence movement.
- This only repairs Tk-less test-object optional-widget guards.
