# MSN Live Run Binder Commands

Use the binder on an existing MSN output folder after the normal MSN adapter tools have produced article, comments, archive, media, acceptance, promotion, and certification outputs.

Example:

```cmd
python source_msn_adapter_live_run_binder.py --root "C:\path\to\MSN_OUTPUT" --out "C:\path\to\MSN_OUTPUT\FINAL_BINDER"
```

The output folder will contain:

- `MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.json`
- `MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.md`
- `MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER_FILES.csv`
- `MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER_NOTES.txt`

A binder that has no positive live evidence remains pending. This is deliberate.
