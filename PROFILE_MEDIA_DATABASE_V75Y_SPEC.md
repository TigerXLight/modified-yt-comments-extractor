# V75Y — Profile/Media Database Mode View Pack

V75Y adds a UI-neutral main-panel view model for Database mode. It bridges the
read-only V75W index and V75X search layer into case, source, and profile
sections that the GUI can later render when the sidebar square toggle is set to
DATABASE.

This is not a sidebar preview and not a sidebar filter. The sidebar remains
mode-only: DATABASE On/Off.

## Added files

- `profile_media_database_mode.py`
- `profile_media_database_mode_test.py`
- `tools/run_profile_media_database_mode_cli_v75y.py`
- `PROFILE_MEDIA_DATABASE_V75Y_SPEC.md`

## Safety boundaries

V75Y does not:

- scan folders
- create folders
- move folders
- rename folders
- copy media
- download media
- classify automatically
- infer sensitive identifiers
- write files during normal view construction

All rows are built from explicit case batch JSON inputs or in-memory payloads.

## View sections

The view contains three sections:

1. `Cases`
2. `Sources`
3. `Profiles`

Case rows remain visible for context even when source/profile search criteria
filter the matched source/profile rows.
