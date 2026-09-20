# R45R Facebook local-exhaust downward fix

R45Q correctly removed the global jump-back-up rescan, but `--progressive-top-down-sweeps 1` also limited local exhaustion to one pass. On Facebook this could leave newly exposed controls such as `View all 71 replies` or `View all 6 replies` visible in the same area after the frontier had already moved down.

R45R keeps the single downward frontier but decouples local exhaustion from global sweep count. Each current visible area gets repeated local passes before scrolling further down. It also resets the initial frontier to the earliest loaded position at the start of expansion, without performing any later global rescan.

Safety properties remain unchanged: visible-page clicks only; no hidden APIs; no cookies/tokens/profile parsing.
