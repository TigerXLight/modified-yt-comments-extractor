# V75E Profile/Media Reviewed Folder Operations

V75E adds the first review-gated folder operation layer for the Profile/Media local database work.

## Scope

This patch supports planning and guarded execution of folder rename/move operations that have already passed review. It does not scan case folders, does not classify sources automatically, and does not infer sensitive identifiers.

## Terminology preserved

- `Database/Profiles` is the global/header profile collection across cases.
- Each case folder has its own `Profiles` folder containing profile information extracted from that case only.
- Case folders retain the structure:
  - `Profiles`
  - `People`
  - `Sources/Articles`
  - `Sources/Social Media/Offline`
  - `Sources/Social Media/Online`
  - `Sources/Internal Media`
  - `Reference Extants`
- `Source: [Name of source page]` may point to Articles, Social Media, or Internal Media.

## Added structures

- `FolderOperationType`
- `FolderOperationStatus`
- `ProfileMediaFolderOperation`
- `ProfileMediaFolderOperationResult`

## Added helpers

- `build_folder_operation_from_review_item(...)`
- `build_folder_operations_from_review_queue(...)`
- `validate_folder_operation_preconditions(...)`
- `apply_folder_operation(...)`
- `build_audit_event_for_folder_operation_result(...)`

## Safety model

By default, operations are inert dry-runs. A folder move/rename can occur only when all of these are true:

1. The review item is `APPROVED_FOR_ACTION`.
2. The review item has `user_confirmation_recorded=True`.
3. The operation is built with `allow_execute=True`.
4. The operation is built with `dry_run_only=False`.
5. `apply_folder_operation(..., execute=True)` is called.
6. The source exists.
7. The destination does not already exist.
8. The destination parent exists, or `create_parent=True` is explicitly supplied.

The default behavior is still no filesystem change.

## Tests

The test suite verifies:

- Dry-run operations do not move folders.
- Unapproved review items are blocked.
- Approved review items can create an operation.
- Missing destination parents block execution unless `create_parent=True` is supplied.
- Temporary test folders can be moved only under explicit execution mode.
- Audit events record whether the operation actually performed a move.
