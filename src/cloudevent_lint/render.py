"""Payload-safe text, JSON, and SARIF renderers."""

from __future__ import annotations

import json

from . import __version__
from .lint import rule_description
from .model import Report


def render_text(report: Report, *, strict: bool = False, quiet: bool = False) -> str:
    """Render findings and a concise summary without event data."""

    lines: list[str] = []
    for finding in report.findings:
        location = f"{finding.file}:{finding.path}"
        if finding.line is not None:
            location += f" (line {finding.line}"
            if finding.column is not None:
                location += f", column {finding.column}"
            location += ")"
        marker = "error" if finding.severity == "error" else "warning"
        lines.append(f"{marker}: {location} [{finding.code}] {finding.message}")
    if not quiet or lines:
        outcome = "failed" if report.exit_code(strict=strict) else "passed"
        lines.append(
            f"{outcome}: {report.files_scanned} file(s), {report.events_checked} event(s), "
            f"{report.errors} error(s), {report.warnings} warning(s)"
        )
    return ("\n".join(lines) + "\n") if lines else ""


def render_json(report: Report) -> str:
    return json.dumps(report.as_dict(), indent=2, sort_keys=False) + "\n"


def _sarif_rule(code: str) -> dict[str, object]:
    return {
        "id": code,
        "shortDescription": {"text": rule_description(code)},
        "helpUri": "https://github.com/thisbejim/cloudevent-lint#rules",
    }


def render_sarif(report: Report) -> str:
    """Render SARIF 2.1.0 suitable for GitHub code scanning."""

    codes = list(dict.fromkeys(finding.code for finding in report.findings))
    results: list[dict[str, object]] = []
    for finding in report.findings:
        result: dict[str, object] = {
            "ruleId": finding.code,
            "level": "error" if finding.severity == "error" else "warning",
            "message": {"text": finding.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file},
                        "region": {
                            **({"startLine": finding.line} if finding.line is not None else {}),
                            **(
                                {"startColumn": finding.column}
                                if finding.column is not None
                                else {}
                            ),
                        },
                    },
                    "logicalLocations": [{"fullyQualifiedName": finding.path}],
                }
            ],
        }
        if finding.record is not None:
            result["properties"] = {"record": finding.record}
        results.append(result)
    document: dict[str, object] = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "cloudevent-lint",
                        "version": __version__,
                        "informationUri": "https://github.com/thisbejim/cloudevent-lint",
                        "rules": [_sarif_rule(code) for code in codes],
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(document, indent=2) + "\n"
