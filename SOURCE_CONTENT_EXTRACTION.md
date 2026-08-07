# Shared source content extraction

This section defines the adapter-neutral content extraction boundary after shared source artifact collection.

- Input is explicit operator-supplied artifacts or a source artifact collection manifest.
- The extractor reads only named files supplied by the operator or manifest.
- It does not fetch URLs, does not launch browsers, does not scan folders, does not read credentials, and does not claim source verification.
- Output is a deterministic content extraction packet with safe artifact basenames, extracted title/body/source metadata, an extraction handoff, store output, CLI, and verifier.
- Future source adapters should use adapter metadata and fixtures unless a site has a genuinely unique extraction surface.
