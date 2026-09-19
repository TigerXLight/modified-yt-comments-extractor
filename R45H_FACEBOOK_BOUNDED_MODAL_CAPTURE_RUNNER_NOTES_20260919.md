# R45H Facebook bounded modal capture runner

R45H follows R45G after live testing showed the runner could appear stuck after visible hidden replies were opened. The problem is not necessarily a browser freeze: the expansion JavaScript can keep running silently inside `page.evaluate` for many stable modal-scroll rounds.

R45H adds:

- bounded auto-expand runtime with `--expand-max-seconds`;
- browser-console progress heartbeats prefixed `R45H_PROGRESS`;
- shorter stability defaults;
- capture-after-timeout behaviour so the current loaded DOM/text/screenshots are still saved;
- the existing R45G hidden-replies/hidden-comments/modal-progress safety contract.

Safety remains unchanged: visible page controls only, no hidden Facebook APIs, no login automation, no cookies/tokens/profile file parsing, and no remote media downloads.
