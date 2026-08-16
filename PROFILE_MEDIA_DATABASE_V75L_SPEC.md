# Profile/media Database V75L — mode-only sidebar correction

V75L preserves the user's corrected UI requirement: the left sidebar Database control is only a mode On/Off switch above FILES.

## Required sidebar shape

```text
DATABASE
  On / Off
FILES
```

## Explicitly not included in the sidebar

- No preview-only label.
- No Database tree preview panel.
- No preview filter box.
- No clear-filter button.
- No folder scan, folder creation, moving, renaming, copying, automatic classification, or sensitive identifier inference.

The database tree/view-model code remains available for future full Database-mode panes, CLI output, and non-sidebar views. The sidebar itself only controls whether the application is in FILES mode or DATABASE mode.
