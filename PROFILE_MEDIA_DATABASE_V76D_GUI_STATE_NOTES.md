# V76D GUI state notes

The Database workbench now has three layers:

1. **Sidebar mode** — the existing `DATABASE` On/Off square toggle.
2. **Main panel** — the V76C workbench panel in the main content area.
3. **Explicit GUI state** — V76D remembers selected batch JSON files and a database root string.

The saved state file does not mean the program has permission to scan a database folder. It only reuses previously selected batch JSON paths. Missing or invalid JSON files are rejected by the batch import assistant and surfaced as warnings.

The Clear batch action clears the in-memory GUI selection and clears the persisted state with the explicit clear confirmation used internally by the action. It does not delete batch JSON files.

The persistence layer deliberately keeps source/profile/case records inside explicit batch JSON. It does not turn the local filesystem into an implicit database search target.
