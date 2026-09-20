# R45V Facebook Playwright mouse downward expand fix — 2026-09-20

R45V uses Playwright-side visible mouse clicks for the first visible Facebook expand control, then rescans the same viewport before scrolling downward. It avoids in-page synthetic click dispatch on Comet role=button controls.

Runtime emits `R45V_PLAYWRIGHT_MOUSE_DOWNWARD_EXPAND_START`, `R45H_PROGRESS {"event":"R45V_MOUSE_CLICK", ...}`, and `R45H_PROGRESS {"event":"R45V_DOWNWARD_SCROLL", ...}`.
