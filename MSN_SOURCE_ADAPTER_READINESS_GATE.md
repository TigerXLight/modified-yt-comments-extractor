# MSN Source Adapter Readiness Gate

Baseline: `e9f6c671b82a429855dbd48d326aa7686c174bf4` (`Complete MSN source adapter media provenance`).

This gate is a structural/offline confidence check for the MSN source adapter. It verifies that one adapter bundle can link:

- article extraction,
- comments/profile provenance,
- offline webpage/archive viewer artifacts,
- media discovery/download registration,
- source-role and media source-chain limits.

It does not run live MSN capture and does not claim WACZ replay success. WARC.GZ remains partial unless manually reviewed in ReplayWeb.page. Media candidates without local paths/hashes remain discovered/registered only, not downloaded evidence files.

For reposted MSN articles, preserve the distinction between the MSN surface, the visible publisher such as The Independent, media credits such as Google Street View, and the still-unlocated original authored/media source.
