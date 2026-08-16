# V75X Profile/Media Database Search Pack

V75X adds a read-only query layer for the Profile/Media Database index created in V75W.

## Added files

- `profile_media_database_search.py`
- `profile_media_database_search_test.py`
- `tools/run_profile_media_database_search_cli_v75x.py`

## Purpose

The search pack lets Database mode query explicit batch-index data by:

- profile name
- case title
- source bucket
- source role
- claim basis
- currentness status
- free text over indexed row fields
- source-chain gap state
- disputed framing state
- profile parser-warning state

This is a backend/query layer, not a sidebar preview or sidebar filter.

## Safety guarantees

V75X does not:

- scan folders
- create folders
- move folders
- rename folders
- copy media
- download media
- classify automatically
- infer sensitive identifiers

The CLI only reads explicit batch JSON files supplied by the user or a demo batch JSON file it writes when requested with `--write-demo-batch`.
