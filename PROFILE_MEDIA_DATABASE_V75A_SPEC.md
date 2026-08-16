# Profile Media Database V75A

V75A defines the local-only foundation for Profile Collection / Database mode.
It preserves the project terminology that this system handles **media** and
profile/case management records. It does not rename the workflow into a server
or external database.

## Root structure

At the database root there is a top-level, non-nested `Profiles` collection.
That header-level collection is for whole-profile files: a new-to-old collection
of person identifiers codified to individual names across cases.

```text
Database/
  Profiles/
  Cases or generated category trees...
```

## Case structure

Each case folder may contain a case-local `Profiles` folder. This is limited to
information extracted from that case only. It is not the same thing as the
header-level `Database/Profiles` collection.

```text
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

External media is accounted for through the non-internal source folders.
`Internal Media` is reserved for media created or obtained by the case creator.
`Reference Extants` stores easy-to-read organised text/descriptive extants that
correlate to people or the case.

## Source classification

The schema stores user-specified source roles and claim basis fields:

- `PRIMARY_SELF_AUTHORED_SCOPE`: authored source only for the author's own
  experiences/perspective.
- `SECONDARY_WITNESS_ACCOUNT`: a witness account observing the primary person or
  event.
- `TERTIARY_PROPAGATED_SOURCE`: authority, family, agency, or outside retelling.
- `UNKNOWN_SOURCE_ROLE`: role not established.

Related flags include source-chain gaps, disputed framing, notes on context
handling, confidence/verification notes, and current/historical/undated status.

## Safety boundary

V75A does not scan arbitrary folders, create folders, move files, rename folders,
fetch sources, classify automatically, infer sensitive attributes, or wire the
GUI. It only creates schema/parser/path-plan contracts and tests.
