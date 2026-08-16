# V76C GUI integration notes

This note is intentionally included with the patch because V76C is the first
Database-mode change that touches the real main window.  It records the
boundaries that future packs must preserve.

## GUI boundary

The sidebar remains a mode switch only.  It should not become a miniature
database browser, text preview, or search form.  The main Database workbench is
where dashboard counts, navigation targets, review lanes, source buckets, source
roles, claim-basis views, currentness status views, and saved views should be
rendered.

## Explicit batch JSON only

V76C introduces selection of explicit batch JSON files.  The selection action is
a file dialog chosen by the user.  It does not walk the database root.  It does
not auto-discover case folders.  It does not infer that a folder should be
imported based on its name.

## Future V76D/V76E boundary

The next packs may add a real import assistant and existing-folder planner, but
they must keep these split responsibilities:

- explicit batch JSON import: user selected files only
- existing-folder planner: dry-run only until a later explicit apply workflow
- materialize/apply workflow: confirmation phrase required
- reviewed move/rename workflow: planned separately and never automatic

## Safety invariants

Every GUI-bound payload should continue to expose these booleans so tests can
verify the UI did not accidentally trigger irreversible work:

```text
folder_scan_performed
folder_creation_performed
folder_move_performed
folder_rename_performed
file_copy_performed
file_write_performed
media_download_performed
automatic_classification_performed
sensitive_identifier_inference_performed
```

## Panel row order

The main content row order after V76C is:

```text
row 0 Source URLs
row 1 Progress / quick panel buttons
row 2 Database Workbench
row 3 Text Editor
row 4 Transcript
row 5 Activity Log
```

## Manual test idea

After applying V76C, turn DATABASE on from the sidebar.  The Database Workbench
panel should appear in the main content area.  Click Load batch JSON and select
`testdata/profile_media_database_v76c_gui_batch_fixture.json`.  The panel should
populate counts from explicit JSON, while the activity log should state that no
folder scan or filesystem mutation was performed.

- Integration note 01: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 02: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 03: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 04: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 05: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 06: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 07: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 08: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 09: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 10: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 11: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 12: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 13: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 14: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 15: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 16: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 17: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 18: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 19: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 20: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 21: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 22: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 23: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 24: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 25: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 26: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 27: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 28: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 29: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 30: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 31: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 32: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 33: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 34: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 35: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 36: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 37: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 38: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 39: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 40: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 41: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 42: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 43: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 44: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 45: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 46: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 47: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 48: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 49: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 50: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 51: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 52: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 53: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 54: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 55: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 56: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 57: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 58: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 59: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 60: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 61: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 62: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 63: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 64: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 65: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 66: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 67: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 68: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 69: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 70: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 71: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 72: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 73: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 74: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 75: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 76: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 77: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 78: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 79: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 80: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 81: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 82: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 83: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 84: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 85: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 86: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 87: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 88: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 89: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 90: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 91: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 92: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 93: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 94: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 95: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 96: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 97: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 98: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 99: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 100: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 101: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 102: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 103: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 104: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 105: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 106: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 107: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 108: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 109: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 110: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 111: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 112: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 113: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 114: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 115: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 116: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 117: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 118: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 119: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.
- Integration note 120: preserve explicit-source, case-local/global-profile, review-lane, and source-role boundaries.