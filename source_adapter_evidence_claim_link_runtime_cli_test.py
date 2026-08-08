import io
import json
import tempfile
from contextlib import redirect_stdout

from source_adapter_evidence_claim_link_runtime_cli import main

buf = io.StringIO()
with redirect_stdout(buf):
    rc = main(["--json"])
assert rc == 0
payload = json.loads(buf.getvalue())
assert payload["verification"]["verified"], payload
with tempfile.TemporaryDirectory() as tmp:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--json", "--store-dir", tmp])
    assert rc == 0
    payload = json.loads(buf.getvalue())
    assert payload["store"]["store_status"] == "STORED", payload
print("Source Adapter Evidence Claim Link Runtime CLI self-test passed.")
