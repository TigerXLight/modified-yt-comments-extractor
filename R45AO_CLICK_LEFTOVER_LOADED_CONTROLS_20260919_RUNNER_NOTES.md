# R45AO click leftover loaded Facebook expansion controls

R45AO keeps the R45AM/R45AN autostart flow and adds a second pass before visual cleanup:

- Count all loaded `View all`, `View hidden`, `View more`, `View N replies`, and `Name replied · N replies` labels across the loaded comments surface.
- If any remain, scroll each leftover label into view and click it before the preserved visual cleanup.
- Recount and print `R45AO_AFTER_LEFTOVER_MISSED_REPORT` before the operator pause.

Safety remains visible-page only: no hidden Facebook/Graph API, no cookie/token/profile parsing, no login automation.
