# Profile/Media Database V76D — GUI state/project pack

V76D adds a larger integration layer on top of the V76C main GUI panel.

## Added

- `profile_media_database_gui_state_store.py`
- `profile_media_database_gui_controller.py`
- GUI state store tests
- GUI controller tests
- `main.py` persistence hooks
- a Clear batch action in the main Database workbench panel
- `tools/run_profile_media_database_gui_state_cli_v76d.py`
- `testdata/profile_media_database_v76d_gui_state_fixture.json`
- `testdata/profile_media_database_v76d_large_project_fixture.json`

## Behaviour

The GUI can remember the explicit batch JSON files selected by the user and restore that Database workbench selection later. The state store persists only app GUI configuration; it is not a case-folder materializer and does not import folders automatically.

## Guardrails

The V76D controller and state store do not scan folders, move folders, rename folders, copy media, download media, auto-classify records, or infer sensitive identifiers. State-file writes require the explicit confirmation phrase `SAVE_PROFILE_MEDIA_GUI_STATE`; state clearing requires `CLEAR_PROFILE_MEDIA_GUI_STATE`.

The main panel remains in the main content area. The left sidebar remains mode-only.
