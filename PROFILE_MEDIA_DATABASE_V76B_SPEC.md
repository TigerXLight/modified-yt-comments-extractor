# PROFILE_MEDIA_DATABASE_V76B_SPEC

## Pack
V76B — Profile/media integration readiness pack.

## Purpose
This pack replaces a loose set of manual checks with one large integration/readiness layer. It proves the V75 and V76 Database-mode backend pieces can be exercised together before the real GUI Database workbench panel is wired.

## Covered in one pack
- full profile/media Database regression command
- combined smoke-test modules
- safety invariant audit
- implementation readiness report
- roadmap/status markdown
- large explicit batch fixture
- CLI proof tool

## Non-goals and safety boundaries
The default path does not scan folders, create folders, move folders, rename folders, copy media, write files, download media, classify automatically, or infer sensitive identifiers.

The regression uses explicit batch JSON input only. It tests that guarded export planning remains dry-run by default and that a wrong confirmation phrase is blocked.

## Added files
- `profile_media_database_safety_invariants.py`
- `profile_media_database_safety_invariants_test.py`
- `profile_media_database_implementation_readiness.py`
- `profile_media_database_implementation_readiness_test.py`
- `profile_media_database_regression.py`
- `profile_media_database_regression_test.py`
- `tools/run_profile_media_full_regression_cli_v76b.py`
- `testdata/profile_media_database_v76b_integration_batch_fixture.json`
- `PROFILE_MEDIA_DATABASE_V76B_SPEC.md`
- `PROFILE_MEDIA_DATABASE_V76B_ROADMAP_STATUS.md`

## Expected CLI result
The proof command should show:
- `profile_media_database_safety_invariants v76b OK`
- `profile_media_database_implementation_readiness v76b OK`
- `profile_media_database_regression v76b OK`
- JSON status `success`
- safety audit status `passed`
- readiness status `ready_for_gui_panel_integration`

## Next phase after V76B
V76C should wire the main GUI Database workbench panel. The sidebar must remain a mode switch only. The Database content belongs in the main area.
