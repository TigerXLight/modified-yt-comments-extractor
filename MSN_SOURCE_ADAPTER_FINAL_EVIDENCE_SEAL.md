# MSN Source Adapter Final Evidence Seal

This file documents the final no-network evidence-seal layer for the MSN source adapter.

The seal is intentionally conservative. It does **not** mark live MSN operation as complete merely because the offline fixtures and generated reports pass. It scans an existing MSN output/package folder and looks for:

- automated report outputs from the final validator, acceptance suite, done gate, operator final runner, live reconciler, closeout orchestrator, final lock, regression index, and evidence pack index;
- filled manual/live acceptance result files;
- article, comments, profile, offline viewer, archive, media, video, source-chain, provenance, package, and report evidence;
- explicit MSN republisher / visible publisher / original source separation;
- media hash/download status where present;
- video/HLS/DASH/poster status where present.

## Final status rules

The seal may emit these final states:

- `COMPLETE_WITH_MANUAL_EVIDENCE`: automated outputs are acceptable and a positive filled manual/live evidence result is present.
- `CONFIDENT_WITH_MANUAL_REVIEW`: automated outputs are acceptable, but positive filled manual/live evidence is missing or still unclear.
- `BLOCKED`: a manual/live result or automated report has a failing/blocking status.
- `PARTIAL`: evidence exists, but some required areas remain incomplete or unclear.
- `INSUFFICIENT_EVIDENCE`: the output folder does not contain enough report evidence to make a meaningful decision.

## Command

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_final_evidence_seal.py "C:\path\to\msn_output_folder"
```

Optional output directory:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_final_evidence_seal.py "C:\path\to\msn_output_folder" --output-dir "C:\path\to\msn_output_folder\reports"
```

## Outputs

- `MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.json`
- `MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.md`
- `MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL_AREAS.csv`

## Safety rule

Do not call real MSN operation complete unless the seal reaches `COMPLETE_WITH_MANUAL_EVIDENCE`. Anything else means the code is structurally strong but still needs live/manual evidence or remediation.
