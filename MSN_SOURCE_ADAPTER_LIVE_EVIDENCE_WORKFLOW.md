# MSN Source Adapter Live Evidence Workflow

The final live MSN state has three separate layers:

1. **Release-candidate lock**: no-network adapter structure and reports are present.
2. **Positive manual/live evidence**: an operator validates a real MSN article output folder and fills the live-evidence result file.
3. **Certification archive**: final reports and hashes are packaged for handoff.

The adapter must not treat fixtures or generated templates as live success. The live evidence result must explicitly pass:

- article extraction;
- comments/profile extraction;
- offline viewer/archive;
- media registration/download status;
- source-chain/provenance separation.

The operator quickstart generator exists so a single output folder can be driven through the final steps without repeating command syntax from memory.
