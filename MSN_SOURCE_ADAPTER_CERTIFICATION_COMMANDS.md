# MSN Source Adapter Certification Commands

These are operator commands for the final MSN adapter phase.

## 1. Build final operator reports

```cmd
python source_msn_adapter_operator_final_runner.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\operator_final"
```

## 2. Reconcile live/manual evidence

```cmd
python source_msn_adapter_live_result_reconciler.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\live_reconciliation"
```

## 3. Run release promotion gate

```cmd
python source_msn_adapter_release_promotion.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\release_promotion"
```

## 4. Run final promotion closeout

```cmd
python source_msn_adapter_final_promotion_closeout.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\promotion_closeout"
```

## 5. Build certification bundle

```cmd
python source_msn_adapter_certification_bundle.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\final_certification"
```

## 6. Build hash-indexed archive

```cmd
python source_msn_adapter_certification_archive.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\certification_archive" --zip
```
