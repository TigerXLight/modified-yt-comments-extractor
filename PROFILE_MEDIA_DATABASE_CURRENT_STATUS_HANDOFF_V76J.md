# Profile/Media Database Current Status Handoff V76J

Latest completed chain:

- V75A-V75P: DATABASE mode foundation, sidebar mode switch, persisted runtime state.
- V75Q-V75Z: case workspace, source/profile intake, manifest/materialize planning, batch/index/search/session/export.
- V76A-V76D: workbench, integration readiness, main GUI panel, GUI state/project restore.
- V76E-V76I: existing-folder planner, controlled materialize, reviewed folder operations, end-to-end proof, reconciliation closeout.
- V76J: manual GUI smoke readiness and final handoff.

Core invariant: explicit user/batch input is the source of truth. The Database workflow must not infer sensitive identifiers from names/appearance and must not silently crawl folders or download media.

For a new session, upload `main.py`, all `profile_media*.py`, matching tests, `tools/run_profile_media*.py`, `PROFILE_MEDIA_DATABASE_*.md`, and `testdata/profile_media_database*.json`. Do not upload `venv`, `dist`, `build`, `.git`, browser profiles, credentials, third-party runtimes, or downloaded media unless specifically needed.
