# MSN Source Adapter Operator Final Commands

Use these commands after the final-lock patch is committed.

## Check repository status

```cmd
git -C "T:\References\to go\Media\tools\Modified YouTube comment extractor" status --short
```

## Build a regression index

```cmd
python "T:\References\to go\Media\tools\Modified YouTube comment extractor\source_msn_adapter_regression_index.py" --repo-root "T:\References\to go\Media\tools\Modified YouTube comment extractor" --output "%USERPROFILE%\Downloads\msn_adapter_regression_index"
```

## Build a final lock report against an output folder

Replace `C:\path\to\MSN_OUTPUT_FOLDER` with the existing MSN bundle/output folder.

```cmd
python "T:\References\to go\Media\tools\Modified YouTube comment extractor\source_msn_adapter_final_lock.py" --target "C:\path\to\MSN_OUTPUT_FOLDER" --repo-root "T:\References\to go\Media\tools\Modified YouTube comment extractor"
```

## Build an evidence pack index

```cmd
python "T:\References\to go\Media\tools\Modified YouTube comment extractor\source_msn_adapter_evidence_pack_index.py" --root "C:\path\to\MSN_OUTPUT_FOLDER"
```

These commands do not start a live capture and do not access the network.
