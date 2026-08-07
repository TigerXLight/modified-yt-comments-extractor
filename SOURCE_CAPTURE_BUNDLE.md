# Shared Source Capture Bundle

This shared module turns adapter-neutral content extraction and comment extraction JSON into a deterministic source capture bundle for Total Export.

It is designed for the one-framework/many-adapters path: new source adapters should provide adapter metadata and fixtures, then use the shared artifact, content, comment, capture-bundle, review, release, and archive contracts instead of cloning the MSN manual implementation chain.

Safety boundary: this module only consumes explicit JSON inputs supplied by the operator or prior pipeline stages. It does not fetch URLs, launch a browser, scan folders, read credentials, submit archive requests, or serialize full local paths.

Outputs include a capture bundle JSON, capture manifest JSON, Total Export handoff JSON, and operator summary JSON.
