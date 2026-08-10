# MSN Source Adapter Regression Index

This patch adds a regression index generator so the final adapter surface can be checked without remembering every file by hand.

`source_msn_adapter_regression_index.py` scans the repository for the MSN modules added during the article/comments/archive/media/source-chain/readiness/acceptance/closeout work.

It writes:

- `MSN_SOURCE_ADAPTER_REGRESSION_INDEX.json`
- `MSN_SOURCE_ADAPTER_REGRESSION_INDEX.md`

The goal is not to prove live site behaviour. The goal is to prove that the expected adapter implementation surface and companion tests have not silently disappeared.
