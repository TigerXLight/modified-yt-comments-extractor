# MSN Source Adapter Post-Certification Audit

This audit is a no-network repo-side preservation guard. It checks that the MSN adapter modules, tests, and documentation added during the closeout work still exist.

It is designed for later roadmap work so MSN coverage is not accidentally lost while moving on to other source adapters or evidence-database tasks.

## Typical command

```cmd
python source_msn_adapter_post_certification_audit.py --repo "T:\References\to go\Media\tools\Modified YouTube comment extractor" --out "T:\References\to go\Media\tools\Modified YouTube comment extractor\msn_post_certification_audit"
```

The audit writes:

- `MSN_SOURCE_ADAPTER_POST_CERTIFICATION_AUDIT.json`
- `MSN_SOURCE_ADAPTER_POST_CERTIFICATION_AUDIT.md`
- `MSN_SOURCE_ADAPTER_POST_CERTIFICATION_AUDIT.csv`

## Boundary

The audit only checks repository artifacts. It cannot certify a live MSN page. Certification still requires positive live/manual evidence.
