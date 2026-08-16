# Profile/Media Database V76G — reviewed folder operations

V76G adds a guarded reviewed-folder-operation workflow for Profile/Media Database mode.

## Scope

- build dry-run folder rename/move plans from explicit operation JSON
- reject absolute paths and parent-directory escape attempts
- require existing source folders and existing destination parents
- block when a destination already exists
- execute only after exact confirmation
- expose a GUI-safe payload for the main Database workbench
- add a main workbench action for reviewed folder operations

## Confirmation phrase

```text
APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS
```

Without this exact phrase, execution is blocked.

## Non-goals / safety invariants

V76G does not scan folders, create folders, copy files, write metadata files,
download media, classify automatically, infer sensitive identifiers, or repair
unreviewed folders.  It only moves or renames folders explicitly supplied in the
reviewed operation JSON after confirmation.
