# R45M Facebook Playwright viewport launch fix — 2026-09-19

## Problem

A manual R45J live run failed before opening the operator-controlled browser page:

```text
TypeError: BrowserType.launch() got an unexpected keyword argument 'viewport'
```

The R45L runner passed `viewport=None` inside the keyword dictionary supplied to
`p.chromium.launch(...)`. In Playwright Python, viewport belongs on browser
contexts, not `BrowserType.launch()`.

## Fix

R45M separates launch and context options:

- `launch_kwargs`: `headless=False`, `--start-maximized`, optional executable path.
- `context_kwargs`: `viewport=None`.
- non-persistent mode: `p.chromium.launch(**launch_kwargs)` then `browser.new_context(**context_kwargs)`.
- persistent mode: `p.chromium.launch_persistent_context(..., **launch_kwargs, **context_kwargs)`.

## Scope

This is a live-run startup hotfix only. It does not change comment expansion,
visual cleanup, comments-column cropping, screenshot naming, or safety policy.

## Safety

No browser profiles are copied, read, or parsed by the tool. No cookies/tokens,
WebView2 storage, hidden Facebook APIs, login automation, or remote media
downloads are used.
