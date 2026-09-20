# R45P Facebook reply bucket + max-band screenshot repair

Fixes after live run `facebook_preserved_visual_screenshot_runner_20260920T035237Z`:

- R45N replied-bucket pass clicked the `Fahad Malik replied · 168 replies` text repeatedly but text length did not grow; R45P walks to the nearest actual clickable ancestor rather than treating the text span itself as clickable.
- R45H progressive mode now detects text-bearing span/div controls and clicks their clickable ancestor, so `View hidden replies` and `View all N replies` labels that are not themselves role=button can still be expanded.
- R45H keeps top-to-bottom downward behaviour but permits a bounded second downward rescan after stability, so controls exposed by earlier clicks are not left behind.
- R45O screenshot banding used page-coordinate clips with `full_page=False`; Playwright interpreted high Y clips outside the viewport. R45P resizes the viewport and uses viewport-relative y=0 clips for max-height bands.

Safety boundaries unchanged: visible page clicks only; no hidden platform APIs; no cookie/token/profile-file parsing.
