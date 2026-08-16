# V75R — Profile/media source intake pack

V75R adds guarded source-intake record planning for Profile/Media Database mode.
It works with the V75Q case workspace shape:

```text
Database/
  Profiles/

[Case Folder]/
  Profiles/
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```

## Purpose

A source-intake record represents a media/source item inside a case. It is not a
final evidence determination. It records where the source belongs, what source
role and claim basis have been assigned, whether there is a source-chain gap,
whether framing is disputed, and what verification/corroboration notes exist.

## Source buckets

Supported bucket paths include:

- `Articles`
- `Social Media/Online`
- `Social Media/Offline`
- `Internal Media`
- `Reference Extants`

`Internal Media` is for media created or obtained by the case creator. Other
source buckets are treated as external media containers.

## Source-claim evaluation fields

V75R preserves the existing profile/media terminology:

- `source_role`: primary self-authored scope, secondary witness account,
  tertiary propagated source, or unknown.
- `claim_basis`: self-authored experience, witness account,
  family/authority claim, agency/outside retelling, appearance claim,
  identity claim, user-entered note, or unknown.
- `currentness_status`: current, historical, undated, or unknown.
- `disputed_framing` and `notes_on_context_dispute`.
- `source_chain_gap`.
- `confidence_or_verification_notes`.
- `family_or_authority_claim_basis`.
- `identity_claim_basis`.
- `appearance_claim_basis`.
- `collaboration_or_corroboration_notes`.

## Safety posture

Default mode is dry-run.

V75R does **not**:

- scan folders;
- move folders;
- rename folders;
- copy media;
- download media;
- classify automatically;
- infer sensitive identifiers;
- treat source text as final proof.

Real source-intake record writing requires both:

```text
--execute --confirm-intake CREATE_SOURCE_INTAKE_RECORD
```

When explicitly confirmed, V75R creates only the source item folder and writes:

```text
source_claim_evaluation.json
source_claim_evaluation.txt
```

It still does not copy the original media file.
