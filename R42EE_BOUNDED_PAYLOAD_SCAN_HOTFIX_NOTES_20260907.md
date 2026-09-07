# R42EE bounded payload scan hotfix

R42ED's matrix logic was correct, but the command-line probe used `Path.rglob()` over `profile_media_live_captures`.  On the local Windows tree this can recurse through a junction/reparse directory and crash before reading the already-created role payload.

R42EE changes only the payload discovery path:

- no GUI launch;
- no archive.ph hit;
- no Tor/Camoufox start;
- no OpenClaw/provider call;
- bounded candidate roots only;
- no following symlinks/reparse points;
- depth and directory-count caps;
- latest good payload still selected by role-count/source score.

The archive-role display path remains closed out.  This hotfix lets the R42ED semantic/media matrix probe finish from cached local payloads.
