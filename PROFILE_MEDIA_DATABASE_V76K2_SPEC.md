# V76K2 Profile/Media HOME Repository UI and Source-Criticism Rebase

V76K2 supersedes the earlier V76K UI polish patch.  It preserves the working V76J chain but changes the user-facing model.

## User-facing model

- `DATABASE` means managed HOME repository mode.
- `SAVE` saves/updates the HOME repository structure.
- `Add / Import` is the common-user entry point for source files, pasted URLs, dragged media, existing folders, or an internal import package.
- `batch JSON` and `materialize` are internal implementation terms and should not be shown as common-user labels.
- `case` means classified action/event/time/source context, not simply a person.

## HOME summary UI

The left DATABASE area should show:

- Primary
- Secondary
- Tertiary
- Persons
- Review items

`Cases`, `Sources`, `Profile rows`, `Unknown source roles`, `Source-chain gaps`, and `Disputed framing` remain available in metadata/review files, but they are not the main common-user display.

## Structural evidence model

Evidence is marked structurally:

- Video
- Audio
- Image
- Corroborated text chain with sustainable markings and bias notes

When an image shows a person, the app must record whether that person is affiliated with the evaluated claim.  If not, the row goes to `claim_subject_affiliation_gap`; it is not treated as visual support.

## Article extraction baseline

Allowed baseline extractors:

- `metadata_parser` for canonical/OpenGraph/schema metadata.
- `trafilatura` for article text and metadata extraction.
- `newspaper4k` for article title/byline/date/body fallback.

Excluded as product classification logic:

- FEVER
- AVeriTeC
- MICE benchmark/verdict logic

Those frameworks are not used for source-role or claim-status decisions.

## Safety

This pack does not scan folders, copy media, download media, auto-classify source roles, or infer sensitive identifiers.
