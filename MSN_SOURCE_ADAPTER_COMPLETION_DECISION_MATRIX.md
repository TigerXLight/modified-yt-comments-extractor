# MSN Source Adapter Completion Decision Matrix

The MSN adapter should be called complete only for a validated target bundle when the static adapter reports and the manual/live result agree.

## Status meanings

| Final status | Meaning |
|---|---|
| `COMPLETE` | Static reports and live/manual result are both pass-level. |
| `CONFIDENT_WITH_MANUAL_REVIEW` | Static reports are strong, but the live/manual result is missing or still review-gated. |
| `PARTIAL` | Live result exists, but one or more non-blocking checks are partial. |
| `BLOCKED` | A core static output is missing or failed. |
| `INSUFFICIENT_EVIDENCE` | The folder does not contain enough recognizable MSN adapter outputs to decide. |

## Core requirements

1. Article output exists.
2. Comments output exists.
3. Profiles output exists.
4. Offline viewer or archive output exists.
5. Media inventory/download output exists.
6. Source-role/source-chain fields exist.
7. MSN republisher/source distinction exists.
8. Final validation/acceptance/done-gate outputs exist.
9. Manual/live acceptance result is filled.

## Source chain reminder

Do not flatten source roles:

- MSN page = captured republisher surface.
- Visible publisher, for example The Independent = publisher/source visible on MSN.
- Visible image credit, for example Google Street View = media credit.
- Original source = only located if there is direct evidence of original authored item/media.

Repeated outlet/agency/family/authority claims should not be upgraded into a primary source merely because many reports repeat them.
