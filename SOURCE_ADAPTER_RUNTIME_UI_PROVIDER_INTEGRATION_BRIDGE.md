# Source Adapter Runtime UI Provider Integration Bridge

Shared bridge from accepted Adapter Runtime Receipt Review output into UI/provider integration bindings.

It maps accepted runtime capabilities for URL fetch/load, browser launch, folder scan, Keys/Accounts credential lookup, archive submission, release upload, app/registry mutation, and file-library publication onto shared UI surface IDs and provider entrypoint IDs, then produces an operator-acceptance handoff.

The bridge keeps runtime action IDs, receipt IDs, UI surface IDs, provider surface IDs, and operator action labels together so implementation and fixture evidence remain traceable across adapters.
