"""Command-line interface for cloudevent-lint."""

from __future__ import annotations

import argparse

from . import DEFAULT_MAX_BYTES, __version__
from .render import render_json, render_sarif, render_text
from .scan import scan_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cloudevent-lint",
        description="Validate CloudEvents JSON objects, batches, and JSONL fixtures offline.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="PATH",
        help="JSON/JSONL file, directory, or - for stdin",
    )
    parser.add_argument(
        "--input-format",
        choices=("auto", "json", "jsonl"),
        default="auto",
        help="input encoding (default: infer .jsonl/.ndjson, otherwise JSON)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "sarif"),
        default="text",
        help="report format (default: text)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as failures",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="omit the clean summary in text output",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        metavar="N",
        help=f"maximum bytes read per input (default: {DEFAULT_MAX_BYTES})",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_bytes <= 0:
        parser.error("--max-bytes must be positive")
    try:
        report = scan_paths(
            args.paths,
            input_format=args.input_format,
            max_bytes=args.max_bytes,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.format == "json":
        output = render_json(report)
    elif args.format == "sarif":
        output = render_sarif(report)
    else:
        output = render_text(report, strict=args.strict, quiet=args.quiet)
    if output:
        print(output, end="")
    return report.exit_code(strict=args.strict)
