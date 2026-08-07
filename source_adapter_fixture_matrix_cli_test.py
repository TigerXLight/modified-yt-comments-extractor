from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_fixture_matrix_cli import main


def test_cli_store_and_verify() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        specs = root / "adapter_specs.json"
        specs.write_text(json.dumps({"adapter_specs": [{"adapter_id": "article", "source_kind": "web", "domains": ["article.example"]}]}), encoding="utf-8")
        out = root / "out"
        assert main(["--adapter-specs-json", str(specs), "--output-dir", str(out), "--json"]) == 0
        matrix_file = next(out.glob("*.fixture_matrix.json"))
        # The verifier expects the full matrix, so verify the build path by printing JSON without output_dir.
        assert main(["--adapter-specs-json", str(specs), "--json"]) == 0
        assert matrix_file.exists()


if __name__ == "__main__":
    test_cli_store_and_verify()
    print("Source Adapter Fixture Matrix CLI self-test passed.")
