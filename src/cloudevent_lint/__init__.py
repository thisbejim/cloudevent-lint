"""Offline CloudEvents JSON contract linting."""

from .lint import lint_document, lint_json_text
from .model import Finding, Report
from .scan import DEFAULT_MAX_BYTES, scan_paths

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_MAX_BYTES",
    "Finding",
    "Report",
    "__version__",
    "lint_document",
    "lint_json_text",
    "scan_paths",
]
