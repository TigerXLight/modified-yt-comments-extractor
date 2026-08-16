# V75N — Profile/media square visual Database toggle

This patch keeps the left-sidebar Database control mode-only while making the visual behaviour closer to the supplied square On/Off example.

## Sidebar shape

```text
DATABASE
  [green ✓        ◻]  when Database mode is on
  [red   ◻        ✕]  when Database mode is off
FILES
```

## Preserved constraints

V75N does not add preview, filtering, scanning, folder creation, folder moving, folder renaming, file copying, automatic classification, or sensitive identifier inference.

The button only flips the UI mode state between `FILES` and `DATABASE` through the existing V75H mode coercion layer.
