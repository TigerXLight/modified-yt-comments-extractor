import io
import json
from contextlib import redirect_stdout
from source_adapter_evidence_export_runtime_bridge_cli import main

buf = io.StringIO()
with redirect_stdout(buf):
    rc = main(["--json"])
assert rc == 0
payload = json.loads(buf.getvalue())
assert payload["verification"]["verified"] is True
assert payload["verification"]["evidence_export_queue_row_count"] == 5
print("Source Adapter Evidence Export Runtime Bridge CLI self-test passed.")
