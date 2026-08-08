import io, json
from contextlib import redirect_stdout
from source_adapter_operator_delivery_receipt_closeout_cli import main
buf = io.StringIO()
with redirect_stdout(buf):
    rc = main(["--json"])
assert rc == 0
payload = json.loads(buf.getvalue())
assert payload["verification"]["verified"] is True
assert payload["verification"]["release_section_completion_ready"] is True
print("Source Adapter Operator Delivery Receipt Closeout CLI self-test passed.")
