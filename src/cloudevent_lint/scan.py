"""Filesystem and stdin orchestration for :mod:`cloudevent_lint`."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from .lint import lint_json_text, parse_error_finding
from .model import Report

DEFAULT_MAX_BYTES = 16 * 1024 * 1024
SUPPORTED_SUFFIXES = frozenset({".json", ".jsonl", ".ndjson"})


def _format_for(path: str, requested: str) -> str:
    if requested in {"json", "jsonl"}:
        return requested
    return "jsonl" if Path(path).suffix.lower() in {".jsonl", ".ndjson"} else "json"


def _directory_files(directory: Path) -> list[Path]:
    files: list[Path] = []
    for candidate in directory.rglob("*"):
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(candidate)
    return sorted(files, key=lambda item: item.as_posix())


def _read_bytes(path: Path, max_bytes: int) -> bytes:
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise ValueError(f"input is {len(data)} bytes; maximum is {max_bytes} bytes")
    return data


def _lint_bytes(
    data: bytes,
    *,
    file: str,
    input_format: str,
    report: Report,
) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        report.add(
            parse_error_finding(
                f"input must be UTF-8: {exc.reason}",
                file=file,
                line=exc.start + 1,
            )
        )
        report.input_errors += 1
        return
    findings, count, input_errors = lint_json_text(
        text,
        file=file,
        input_format=_format_for(file, input_format),
    )
    report.extend(findings)
    report.events_checked += count
    report.input_errors += input_errors


def _lint_file(path: Path, *, input_format: str, max_bytes: int, report: Report) -> None:
    display = os.fspath(path)
    report.files_scanned += 1
    try:
        data = _read_bytes(path, max_bytes)
    except (OSError, ValueError) as exc:
        report.add(parse_error_finding(str(exc), file=display))
        report.input_errors += 1
        return
    _lint_bytes(data, file=display, input_format=input_format, report=report)


def scan_paths(
    paths: list[str],
    *,
    input_format: str = "auto",
    max_bytes: int = DEFAULT_MAX_BYTES,
    stdin: io.BufferedIOBase | io.TextIOBase | None = None,
) -> Report:
    """Scan files/directories and optionally stdin into one report."""

    if input_format not in {"auto", "json", "jsonl"}:
        raise ValueError("input_format must be auto, json, or jsonl")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    report = Report()
    for raw_path in paths:
        if raw_path == "-":
            report.files_scanned += 1
            source = stdin if stdin is not None else getattr(sys.stdin, "buffer", sys.stdin)
            try:
                data = source.read()
                if isinstance(data, str):
                    data = data.encode("utf-8")
                if len(data) > max_bytes:
                    raise ValueError(f"input is {len(data)} bytes; maximum is {max_bytes} bytes")
            except (OSError, ValueError) as exc:
                report.add(parse_error_finding(str(exc), file="<stdin>"))
                report.input_errors += 1
                continue
            _lint_bytes(data, file="<stdin>", input_format=input_format, report=report)
            continue

        path = Path(raw_path)
        if path.is_dir():
            files = _directory_files(path)
            if not files:
                report.add(
                    parse_error_finding(
                        "directory contains no .json, .jsonl, or .ndjson files",
                        file=os.fspath(path),
                    )
                )
                report.input_errors += 1
                continue
            for file_path in files:
                _lint_file(file_path, input_format=input_format, max_bytes=max_bytes, report=report)
            continue
        if not path.exists():
            report.add(parse_error_finding("input path does not exist", file=os.fspath(path)))
            report.input_errors += 1
            continue
        if not path.is_file():
            report.add(
                parse_error_finding("input path is not a regular file", file=os.fspath(path))
            )
            report.input_errors += 1
            continue
        _lint_file(path, input_format=input_format, max_bytes=max_bytes, report=report)
    return report
