# V75P — Profile/media runtime mode state pack

V75P persists the left-sidebar **DATABASE On/Off** mode without expanding the sidebar into a preview, filter, scanner, or repository browser.

## Behaviour

- On startup, the app loads the previous FILES/DATABASE mode from a local JSON runtime state file.
- When the user clicks the square Database toggle, only the mode state is saved.
- The mode state records explicit negative safety claims:
  - no folder scan
  - no folder move
  - no folder rename
  - no folder creation
  - no file copy
  - no automatic classification
  - no sensitive identifier inference

## Files added

- `profile_media_database_runtime.py`
- `profile_media_database_runtime_test.py`
- `profile_media_database_sidebar_runtime_state_test.py`
- `tools/run_profile_media_database_runtime_cli_v75p.py`

## UI rule preserved

The sidebar remains mode-only:

```text
DATABASE
  square visual On/Off toggle
FILES
```

No Database preview and no filter are reintroduced.
