# V76E Existing Folder Import Notes

The existing-folder import workflow is intentionally staged:

1. User supplies or exports a folder-tree text listing.
2. V76E parses that explicit listing without scanning the filesystem.
3. The planner creates source/profile/global-profile candidates.
4. The planner builds a batch JSON preview with unknown roles/bases preserved for review.
5. A later guarded workflow may write, load, review, and materialize the preview.

Important behavior:

- Case-local `Profiles` folders become case-local profile candidates.
- Header/global `Database/Profiles` entries become global profile candidates and are not silently linked to a case.
- `Sources/Articles`, `Sources/Social Media/Online`, `Sources/Social Media/Offline`, and `Sources/Internal Media` become source candidates.
- `People` and `Reference Extants` are recognised as review/reference entries, not automatically converted to source/profile rows.
- Existing folder names are not proof of sensitive identifiers. No sensitive inference is performed.
- Existing folder names are not source-role proof. New rows default to `UNKNOWN_SOURCE_ROLE` and `UNKNOWN_CLAIM_BASIS`.

V76E also makes source-role labels safer before the GUI depends on them. The legacy string `SECONDARY_WITNESS_SOURCE` is accepted, but displayed/indexed as `SECONDARY_WITNESS_ACCOUNT`.
