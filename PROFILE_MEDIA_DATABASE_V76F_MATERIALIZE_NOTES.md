# V76F Materialize Notes

V76F is the first pack in this sequence where a confirmed path can intentionally
write to the filesystem.  The operation is still narrow: it creates the expected
Database/case/profile/source folders and writes metadata text/JSON records.  It
is not a media importer and not a filesystem discovery tool.

Recommended user flow:

1. Keep `DATABASE` mode on.
2. Load explicit batch JSON through the main Database workbench.
3. Review the dashboard, navigation targets, and review report.
4. Use `Materialize` only after choosing a real target Database root.
5. Type `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION` exactly.

For existing folders, V76E remains a dry-run planner.  A V76E preview becomes
eligible for V76F only after it is explicitly written as standalone batch JSON
and then selected by the Database batch JSON loader.
