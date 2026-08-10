# MSN Source Adapter Live Acceptance Pack

This operator pack is the manual/live counterpart to the no-network acceptance
suite. It generates a checklist and result templates for a real MSN article
validation run.

It does not start live capture. The operator first runs an approved MSN capture
or export workflow, then uses the generated checklist to record what actually
worked.

The pack keeps the project's source hierarchy intact:

- MSN page: captured platform / possible republisher surface.
- Visible publisher such as The Independent: outside/publisher framing source.
- Visible media credit such as Google Street View: media credit only, not the
  same thing as the original uploader unless proven.
- Missing original source: explicit source-chain gap.

Generated files:

- `01_MSN_LIVE_ACCEPTANCE_CHECKLIST.md`
- `02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json`
- `03_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.md`
- `04_MSN_LIVE_ACCEPTANCE_DECISION_GUIDE.md`

Example:

```cmd
python source_msn_adapter_live_acceptance_pack.py --output "%USERPROFILE%\Downloads\msn-live-acceptance" --article-url "https://www.msn.com/..."
```
