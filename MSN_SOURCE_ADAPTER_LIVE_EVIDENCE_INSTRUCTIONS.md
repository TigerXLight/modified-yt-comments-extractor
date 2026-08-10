# MSN Live Evidence Instructions

This file explains what needs to be placed in an MSN output folder for the closeout orchestrator to call the adapter complete on a real MSN article.

## Required operator evidence

Place one filled live/manual result in the output folder. Accepted filenames include:

- `02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json`
- `MSN_LIVE_ACCEPTANCE_RESULT.json`
- `MSN_SOURCE_ADAPTER_MANUAL_VALIDATION_RESULT.json`
- `operator_result.json`
- any JSON file whose name includes `live`, `manual`, `acceptance`, or `operator_result`

The JSON should contain a clear status or result field such as:

```json
{
  "status": "PASS",
  "live_article_passed": true,
  "article_extraction_passed": true,
  "comments_export_passed": true,
  "offline_viewer_passed": true,
  "media_review_passed": true,
  "source_chain_review_passed": true,
  "notes": "Manual live validation completed on the named MSN article."
}
```

## When the result should not pass

Do not mark the live/manual result as passed when:

- the comments drawer could not be opened,
- nested replies were not captured,
- the page scrolled away from the comments overlay instead of the overlay scrolling,
- profile links or profile rows were missing from a target that visibly had them,
- media candidates were not listed,
- downloaded media lacked path/hash/status where downloads were expected,
- offline viewer HTML was not usable,
- WARC/WACZ statuses were falsely labelled as full success,
- MSN was treated as the primary source for a syndicated/reposted article without evidence,
- visible publisher/source/media-credit/original-source fields were collapsed into one field.

## Expected closeout output

After running the closeout command, review:

- `MSN_SOURCE_ADAPTER_CLOSEOUT_REPORT.md`
- `MSN_SOURCE_ADAPTER_CLOSEOUT_ACTIONS.md`

The first file gives the status. The second file tells the next work item only when the adapter is not complete.
