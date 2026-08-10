# MSN Patch-Kit Discipline

Every future MSN patch kit should follow these rules:

1. Check the exact expected baseline commit.
2. Refuse to run if the working tree is dirty.
3. Copy or apply files.
4. Run `git diff --check`.
5. Compile changed Python files.
6. Run the selected self-tests.
7. Stop immediately on any non-zero exit code.
8. Commit only after all verification commands return zero.
9. Push only after the commit succeeds.
10. Print final `HEAD`, `origin/<branch>`, and `git status --short`.

The final self-test orchestrator is the preferred way to avoid silent failure continuation.
