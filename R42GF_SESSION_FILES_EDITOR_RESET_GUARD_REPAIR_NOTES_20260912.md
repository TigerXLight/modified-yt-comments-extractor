# R42GF session-files editor reset guard repair

This is a second narrow Tk-less session-files guard repair discovered while rerunning the R42GF closeout suite.

## Problem

`session_files_test.py` uses `App.__new__(App)` to exercise session-file intake without constructing a real Tk root. After the transcript-panel guard passed, the next path failed in `_reset_editor_panels_after_file_intake()` because it still used `hasattr(self, "text_editor_status_label")`. On a Tkinter/CustomTkinter-derived object without `self.tk`, `hasattr(...)` can invoke Tkinter `__getattr__` repeatedly and hit `RecursionError`.

## Change

The text-editor reset/show/hide/toggle helpers now consult `self.__dict__` for optional widgets instead of probing Tk attributes. This keeps real UI behaviour while making Tk-less test stubs safe.

## Boundaries

- No Twitter/X route changes.
- No source-family matrix changes.
- No source adapter capability changes.
- No network, browser, API, screenshot, OCR, archive, media download, evidence movement, or classification.
