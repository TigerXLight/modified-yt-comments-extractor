# V75H Profile/Media Database View Model

V75H adds a UI-neutral view model for the future left-panel toggle between
FILES mode and DATABASE mode.

## Purpose

The project needs a lightweight mode switch above the existing FILES area. This
patch does not wire GUI controls yet. It provides stable Python state that GUI
code can render later.

## Model

- `ProfileMediaViewMode.FILES`
- `ProfileMediaViewMode.DATABASE`
- `ProfileMediaDatabaseViewState`
- `build_profile_media_database_view_state(...)`
- `toggle_profile_media_view_mode(...)`
- `filter_database_tree_rows(...)`
- `count_tree_rows_by_type(...)`

## Safety boundaries

The view model is read/view planning only. It does not:

- scan folders
- create folders
- move folders
- rename folders
- copy files
- classify automatically
- infer sensitive identifiers
- fetch sources
- run browser automation
- use credentials

## Hierarchy preserved

The view model preserves the corrected V75G structure:

```text
Database/
  Profiles/

[Case Folder]/
  Profiles/
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```
