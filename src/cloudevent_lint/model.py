"""Public report models used by the linter and its renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class Finding:
    """A single, payload-safe validation finding."""

    code: str
    severity: Severity
    message: str
    file: str
    path: str
    line: int | None = None
    column: int | None = None
    record: int | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a stable machine-readable representation."""

        result: dict[str, object] = {
            "file": self.file,
            "path": self.path,
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.line is not None:
            result["line"] = self.line
        if self.column is not None:
            result["column"] = self.column
        if self.record is not None:
            result["record"] = self.record
        return result


@dataclass
class Report:
    """Aggregated results for one or more input documents."""

    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    events_checked: int = 0
    input_errors: int = 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def extend(self, findings: list[Finding]) -> None:
        self.findings.extend(findings)

    @property
    def errors(self) -> int:
        return sum(finding.severity == "error" for finding in self.findings)

    @property
    def warnings(self) -> int:
        return sum(finding.severity == "warning" for finding in self.findings)

    def exit_code(self, *, strict: bool = False) -> int:
        """Return the documented CLI status code."""

        if self.input_errors:
            return 2
        if self.errors or (strict and self.warnings):
            return 1
        return 0

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON report without event payloads."""

        return {
            "schemaVersion": 1,
            "filesScanned": self.files_scanned,
            "eventsChecked": self.events_checked,
            "errors": self.errors,
            "warnings": self.warnings,
            "inputErrors": self.input_errors,
            "findings": [finding.as_dict() for finding in self.findings],
        }
