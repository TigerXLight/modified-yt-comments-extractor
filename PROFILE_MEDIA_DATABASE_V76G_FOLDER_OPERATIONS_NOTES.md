# V76G reviewed folder operations notes

This pack is intentionally narrower than the V76F materialize workflow.  V76F
creates known database structure and metadata files from explicit batch JSON;
V76G only applies reviewed folder rename/move operations against an already-known
database root.

The CLI and GUI adapter treat the operation JSON as the source of truth.  They do
not discover the database tree by walking folders.  A future GUI can display the
plan, require the confirmation phrase, then refresh the Database workbench after
success.

Supported operation types:

- `rename_folder` with `source_path` and `new_name`
- `move_folder` with `source_path` and `destination_path`

All paths are interpreted as relative to `database_root`; absolute paths and `..`
segments are blocked.
