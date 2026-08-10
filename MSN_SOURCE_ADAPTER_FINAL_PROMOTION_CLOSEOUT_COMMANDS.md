# MSN Source Adapter Final Promotion Closeout Commands

Generate a fillable live evidence template:

```cmd
python source_msn_adapter_live_evidence_template.py --output-dir C:\path\to\msn_output\live_evidence --target-url "https://www.msn.com/..."
```

After the operator fills the evidence JSON and sets `operator_signed` to `true`, run:

```cmd
python source_msn_adapter_final_promotion_closeout.py --root C:\path\to\msn_output --out C:\path\to\msn_output\final_promotion_closeout
```

Read:

- `MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT.json`
- `MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT.md`
- `MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT_CHECKS.csv`

Only `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE` means the live MSN adapter has crossed the final gate.
