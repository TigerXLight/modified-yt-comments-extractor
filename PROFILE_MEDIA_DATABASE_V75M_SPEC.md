# V75M Profile/Media Database Visual Toggle

V75M keeps the Database sidebar as a mode-only control and adjusts the toggle to match the requested on/off behaviour.

## Sidebar behaviour

The sidebar remains limited to:

```text
DATABASE
  ✓ On / ✕ Off switch
FILES
```

The switch uses:

- green on state with a check label;
- red off state with an X label;
- a light switch thumb;
- no preview tree;
- no filter box.

## Safety boundary

This patch does not scan, classify, create folders, rename folders, move folders, copy files, infer sensitive identifiers, or execute database imports. It only changes the visual state of the existing mode toggle.
