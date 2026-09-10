from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

from cloudevent_lint import scan_paths
from cloudevent_lint.render import render_json, render_sarif, render_text

ROOT = Path(__file__).parents[1]


def test_scan_directory_and_renderers() -> None:
    report = scan_paths([str(ROOT / "examples")])
    assert report.files_scanned == 4
    assert report.events_checked == 6
    assert report.errors > 0
    assert "findings" in render_json(report)
    sarif = json.loads(render_sarif(report))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"]
    text = render_text(report)
    assert "payload is never echoed" not in text
    assert "failed:" in text


def test_scan_stdin_and_max_bytes() -> None:
    data = b'{"specversion":"1.0","type":"x","source":"/x","id":"1"}'
    report = scan_paths(["-"], stdin=io.BytesIO(data))
    assert report.exit_code() == 0
    too_small = scan_paths(["-"], stdin=io.BytesIO(data), max_bytes=10)
    assert too_small.exit_code() == 2
    assert too_small.findings[0].code == "CE000"


def test_missing_and_empty_paths_are_input_errors(tmp_path: Path) -> None:
    missing = scan_paths([str(tmp_path / "missing.json")])
    assert missing.exit_code() == 2
    empty = scan_paths([str(tmp_path)])
    assert empty.exit_code() == 2


def test_cli_success_failure_and_machine_output(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(
        json.dumps({"specversion": "1.0", "type": "x", "source": "/x", "id": "1"}),
        encoding="utf-8",
    )
    success = subprocess.run(
        [sys.executable, "-m", "cloudevent_lint", str(valid)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert success.returncode == 0
    assert "passed:" in success.stdout

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    machine = subprocess.run(
        [sys.executable, "-m", "cloudevent_lint", "--format", "json", str(invalid)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert machine.returncode == 1
    payload = json.loads(machine.stdout)
    assert payload["errors"] >= 1
    assert payload["findings"][0]["code"] == "CE100"


def test_cli_strict_warnings_fail(tmp_path: Path) -> None:
    warning = tmp_path / "warning.json"
    warning.write_text(
        json.dumps(
            {
                "specversion": "1.0",
                "type": "x",
                "source": "/x",
                "id": "1",
                "verylongextensionname": "ok",
            }
        ),
        encoding="utf-8",
    )
    normal = subprocess.run(
        [sys.executable, "-m", "cloudevent_lint", str(warning)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    strict = subprocess.run(
        [sys.executable, "-m", "cloudevent_lint", "--strict", str(warning)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert normal.returncode == 0
    assert strict.returncode == 1


def test_quiet_and_forced_jsonl_modes(tmp_path: Path) -> None:
    event_file = tmp_path / "events.data"
    event_file.write_text(
        '{"specversion":"1.0","type":"x","source":"/x","id":"1"}\n',
        encoding="utf-8",
    )
    quiet = subprocess.run(
        [sys.executable, "-m", "cloudevent_lint", "--quiet", str(event_file)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert quiet.returncode == 0
    assert quiet.stdout == ""
    forced = subprocess.run(
        [sys.executable, "-m", "cloudevent_lint", "--input-format", "jsonl", str(event_file)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert forced.returncode == 0
    assert "2 event(s)" not in forced.stdout
    assert "1 event(s)" in forced.stdout
