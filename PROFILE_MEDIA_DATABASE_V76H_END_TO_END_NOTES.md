# V76H End-to-End Notes

V76H is a closeout-style integration pack. It proves the full Profile/Media Database workflow can run in a controlled way from explicit inputs.

## Normal dry-run flow

The user provides an explicit folder-tree text listing. V76H parses that listing into source/profile/global-profile candidates and renders a reviewable plan. No folder scan is performed.

## Preview write flow

The workflow may write one standalone batch-preview JSON file only when the exact phrase `WRITE_EXISTING_FOLDER_BATCH_PREVIEW` is supplied.

## Materialize flow

The workflow may materialize the selected batch JSON only when the exact phrase `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION` is supplied. This can create folders and metadata files, but does not copy or download media.

## Reviewed folder operations flow

The workflow may apply reviewed folder move/rename operations only when the exact phrase `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS` is supplied. All operation paths are explicit and must remain under `database_root`.

## Closeout status

The closeout report does not mutate anything. It summarizes implemented capabilities and identifies the remaining GUI smoke-test tasks.
