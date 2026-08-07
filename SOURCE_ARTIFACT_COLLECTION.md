# Shared Source Artifact Collection

This module is the shared artifact-collection boundary for all source adapters.
It is intentionally adapter-neutral so future websites do not need an MSN-sized
module chain.

The collector reads only explicit operator-supplied files, records safe relative
artifact names, hashes and byte counts, and produces a deterministic collection
manifest that can be handed to shared extraction, Total Export, review, release,
and archive stages.

It does not scan folders, does not fetch URLs, launch browsers, submit archive requests,
read credentials, or mark captures as complete without explicit artifacts.
