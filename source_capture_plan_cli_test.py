import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from source_capture_plan_cli import main


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_path = root / "plan.json"
        _write_json(
            input_path,
            {
                "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
                "source_label": "YouTube clip",
                "title": "Nicolas Cage ZoneX trailer",
                "selected_capture_options": [
                    "comments",
                    "archive_check",
                    "unknown_option",
                    "comments",
                ],
                "user_terms": ["Nyxara", "Freckelston", "Nyxara"],
            },
        )

        code, markdown, stderr = _run_cli(["--input", str(input_path)])
        assert code == 0
        assert stderr == ""
        assert "# Source Capture Plan" in markdown
        assert "Local planning metadata only" in markdown
        assert "Status: ready" in markdown
        assert "Adapter: YouTube (`youtube`)" in markdown
        assert "Selected capture options: comments, archive_check" in markdown
        assert "Unknown capture options: unknown_option" in markdown
        assert "Duplicate capture options: comments" in markdown
        assert "Nyxara" in markdown
        assert "Freckelston" in markdown
        assert "No fetch/capture/network actions are performed" in markdown

        code, text, stderr = _run_cli(
            ["--input", str(input_path), "--format", "text"]
        )
        assert code == 0
        assert stderr == ""
        assert "Source capture plan" in text
        assert "status: ready" in text
        assert "adapter: YouTube (youtube)" in text
        assert "selected_capture_options: comments, archive_check" in text

        code, json_output, stderr = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert list(parsed) == sorted(parsed)
        assert parsed["status"] == "ready"
        assert parsed["adapter_name"] == "youtube"
        assert parsed["selected_capture_options"] == ["comments", "archive_check"]
        assert parsed["unknown_capture_options"] == ["unknown_option"]
        assert parsed["duplicate_capture_options"] == ["comments"]
        assert parsed["context_result"]["glossary_terms"][0]["text"] == "Nyxara"
        assert "No fetch/capture/network actions" in parsed["scope"]

        news_input = root / "news_plan.json"
        _write_json(
            news_input,
            {
                "source_url": "https://www.msn.com/en-gb/news/world/example-story/ar-AA123456?ocid=feeds",
                "source_label": "MSN article",
                "title": "Example news article",
                "selected_capture_options": ["visible_page_text"],
                "user_terms": ["Reporter Name"],
            },
        )
        code, news_json, stderr = _run_cli(
            ["--input", str(news_input), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed_news = json.loads(news_json)
        assert parsed_news["status"] == "ready"
        assert parsed_news["adapter_name"] == "news_website"
        assert parsed_news["adapter_display_name"] == "News Website"
        assert parsed_news["normalized_url"] == (
            "https://www.msn.com/en-gb/news/world/example-story/ar-AA123456"
        )
        assert parsed_news["source_id"] == (
            "www.msn.com/en-gb/news/world/example-story/ar-AA123456"
        )
        assert parsed_news["selected_capture_options"] == ["visible_page_text"]

        output_path = root / "SOURCE_CAPTURE_PLAN.md"
        output_args = ["--input", str(input_path), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith("# Source Capture Plan")

        code, stdout, stderr = _run_cli(output_args)
        assert code == 1
        assert stdout == ""
        assert "output path already exists" in stderr

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "Source Capture Plan" in output_path.read_text(encoding="utf-8")

        missing_input = root / "missing.json"
        code, stdout, stderr = _run_cli(["--input", str(missing_input)])
        assert code == 1
        assert stdout == ""
        assert "input file not found" in stderr

        invalid_input = root / "invalid.json"
        invalid_input.write_text("{not json\n", encoding="utf-8")
        code, stdout, stderr = _run_cli(["--input", str(invalid_input)])
        assert code == 1
        assert stdout == ""
        assert "invalid JSON" in stderr

        list_input = root / "list.json"
        _write_json(list_input, [])
        code, stdout, stderr = _run_cli(["--input", str(list_input)])
        assert code == 1
        assert stdout == ""
        assert "input JSON must be an object" in stderr

        missing_url = root / "missing_url.json"
        _write_json(missing_url, {"source_label": "missing"})
        code, stdout, stderr = _run_cli(["--input", str(missing_url)])
        assert code == 1
        assert stdout == ""
        assert "source_url is required" in stderr

        bad_options = root / "bad_options.json"
        _write_json(
            bad_options,
            {
                "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "selected_capture_options": "comments",
            },
        )
        code, stdout, stderr = _run_cli(["--input", str(bad_options)])
        assert code == 1
        assert stdout == ""
        assert "selected_capture_options must be a list of strings" in stderr

        bad_terms = root / "bad_terms.json"
        _write_json(
            bad_terms,
            {
                "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "user_terms": "Nyxara",
            },
        )
        code, stdout, stderr = _run_cli(["--input", str(bad_terms)])
        assert code == 1
        assert stdout == ""
        assert "user_terms must be a list of strings" in stderr


if __name__ == "__main__":
    run_self_test()
    print("Source capture plan CLI self-test passed.")
