import io, json
from contextlib import redirect_stdout
from source_adapter_release_archive_delivery_runtime_cli import main
buf = io.StringIO()
with redirect_stdout(buf):
    rc = main(["--json"])
assert rc == 0
payload = json.loads(buf.getvalue())
assert payload["verification"]["verified"] is True
assert payload["verification"]["delivery_receipt_row_count"] == 20
print("Source Adapter Release Archive Delivery Runtime CLI self-test passed.")
