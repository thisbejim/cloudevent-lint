"""Pure CloudEvents JSON parsing and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .model import Finding
from .rules import (
    ATTRIBUTE_NAME_RE,
    KNOWN_ATTRIBUTES,
    REQUIRED_ATTRIBUTES,
    RULE_DESCRIPTIONS,
    SPECIAL_MEMBERS,
    media_type_is_json,
    string_issue,
    valid_absolute_uri,
    valid_attribute_scalar,
    valid_base64,
    valid_media_type,
    valid_timestamp,
    valid_uri_reference,
)


class DuplicateMemberError(ValueError):
    """Raised when a JSON object repeats a member name."""

    def __init__(self, member: str) -> None:
        super().__init__(f"duplicate JSON member {member!r}")
        self.member = member


class InvalidConstantError(ValueError):
    """Raised for non-standard JSON constants such as NaN."""


def _object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateMemberError(key)
        result[key] = value
    return result


def parse_json(text: str) -> Any:
    """Parse strict JSON while rejecting duplicate members and NaN/Infinity."""

    def reject_constant(value: str) -> None:
        raise InvalidConstantError(f"non-standard JSON constant {value}")

    return json.loads(text, object_pairs_hook=_object_pairs_hook, parse_constant=reject_constant)


@dataclass(slots=True)
class _Builder:
    file: str
    record: int | None = None
    line: int | None = None
    findings: list[Finding] | None = None

    def __post_init__(self) -> None:
        if self.findings is None:
            self.findings = []

    def add(
        self,
        code: str,
        severity: str,
        message: str,
        path: str,
        *,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        if severity not in {"error", "warning"}:
            raise ValueError(f"unsupported severity {severity!r}")
        assert self.findings is not None
        self.findings.append(
            Finding(
                code=code,
                severity=severity,  # type: ignore[arg-type]
                message=message,
                file=self.file,
                path=path,
                line=self.line if line is None else line,
                column=column,
                record=self.record,
            )
        )


def _string_attribute(
    builder: _Builder,
    value: object,
    path: str,
    *,
    name: str,
    required: bool = False,
) -> bool:
    if not isinstance(value, str):
        builder.add(
            "CE101" if required else "CE170",
            "error",
            f"{name} must be a string",
            path,
        )
        return False
    issue = string_issue(value)
    if issue:
        builder.add("CE130", "error", f"{name} {issue}", path)
    if required and not value:
        builder.add("CE102", "error", f"{name} must be a non-empty string", path)
    return True


def _validate_subject(builder: _Builder, event: dict[str, Any], path: str) -> None:
    value = event.get("subject")
    if value is None or not _string_attribute(builder, value, f"{path}.subject", name="subject"):
        return
    if not value:
        builder.add(
            "CE102",
            "error",
            "subject must be non-empty when present",
            f"{path}.subject",
        )


def _validate_time(builder: _Builder, event: dict[str, Any], path: str) -> None:
    value = event.get("time")
    if value is None or not _string_attribute(builder, value, f"{path}.time", name="time"):
        return
    if not valid_timestamp(value):
        builder.add("CE150", "error", "time must be an RFC 3339 timestamp", f"{path}.time")


def _validate_content_type(builder: _Builder, event: dict[str, Any], path: str) -> str | None:
    value = event.get("datacontenttype")
    if value is None or not _string_attribute(
        builder,
        value,
        f"{path}.datacontenttype",
        name="datacontenttype",
    ):
        return None
    assert isinstance(value, str)
    if not value:
        builder.add(
            "CE102",
            "error",
            "datacontenttype must be non-empty when present",
            f"{path}.datacontenttype",
        )
    elif not valid_media_type(value):
        builder.add(
            "CE160",
            "error",
            "datacontenttype must be a valid RFC 2046 media type",
            f"{path}.datacontenttype",
        )
    return value


def _validate_dataschema(builder: _Builder, event: dict[str, Any], path: str) -> None:
    value = event.get("dataschema")
    if value is None or not _string_attribute(
        builder,
        value,
        f"{path}.dataschema",
        name="dataschema",
    ):
        return
    assert isinstance(value, str)
    if not value:
        builder.add(
            "CE102",
            "error",
            "dataschema must be non-empty when present",
            f"{path}.dataschema",
        )
    elif not valid_absolute_uri(value):
        builder.add("CE141", "error", "dataschema must be an absolute URI", f"{path}.dataschema")


def _validate_event(
    event: object,
    builder: _Builder,
    path: str,
    seen_keys: set[tuple[str, str]],
) -> None:
    if not isinstance(event, dict):
        builder.add("CE002", "error", "batch member must be a JSON object", path)
        return

    for name in event:
        if name in SPECIAL_MEMBERS:
            continue
        if not ATTRIBUTE_NAME_RE.fullmatch(name):
            builder.add(
                "CE120",
                "error",
                "attribute names must use lower-case ASCII letters and digits",
                f"{path}.{name}",
            )
        elif len(name) > 20:
            builder.add(
                "CE121",
                "warning",
                "attribute name exceeds the recommended 20 characters",
                f"{path}.{name}",
            )

    for name in REQUIRED_ATTRIBUTES:
        member_path = f"{path}.{name}"
        if name not in event:
            builder.add("CE100", "error", f"missing required attribute {name}", member_path)
            continue
        if event[name] is None:
            builder.add("CE101", "error", f"{name} must be a string", member_path)
            continue
        _string_attribute(builder, event[name], member_path, name=name, required=True)

    if isinstance(event.get("specversion"), str) and event["specversion"] != "1.0":
        builder.add("CE110", "error", "specversion must be exactly '1.0'", f"{path}.specversion")

    if (
        isinstance(event.get("source"), str)
        and event["source"]
        and not valid_uri_reference(event["source"])
    ):
        builder.add(
            "CE140",
            "error",
            "source must be a non-empty URI-reference",
            f"{path}.source",
        )

    _validate_subject(builder, event, path)
    _validate_time(builder, event, path)
    content_type = _validate_content_type(builder, event, path)
    _validate_dataschema(builder, event, path)

    for name, value in event.items():
        if name in KNOWN_ATTRIBUTES or name in SPECIAL_MEMBERS:
            continue
        if not valid_attribute_scalar(value):
            builder.add(
                "CE170",
                "error",
                "extension attributes must be null, boolean, 32-bit integer, or string",
                f"{path}.{name}",
            )

    has_data = "data" in event
    has_binary_data = "data_base64" in event
    if has_data and has_binary_data:
        builder.add(
            "CE180",
            "error",
            "data and data_base64 cannot both be present",
            path,
        )
    if has_binary_data and (
        not isinstance(event["data_base64"], str) or not valid_base64(event["data_base64"])
    ):
        builder.add(
            "CE181",
            "error",
            "data_base64 must be canonical RFC 4648 base64 text",
            f"{path}.data_base64",
        )
    if has_data and not media_type_is_json(content_type) and not isinstance(event["data"], str):
        builder.add(
            "CE182",
            "error",
            "data must be a string when datacontenttype is not JSON",
            f"{path}.data",
        )

    source = event.get("source")
    identifier = event.get("id")
    if isinstance(source, str) and source and isinstance(identifier, str) and identifier:
        event_key = (source, identifier)
        if event_key in seen_keys:
            builder.add(
                "CE300",
                "warning",
                "source and id repeat an earlier event in this input document",
                f"{path}.id",
            )
        seen_keys.add(event_key)


def lint_document(
    document: object,
    *,
    file: str = "<input>",
    record: int | None = None,
    line: int | None = None,
    seen_keys: set[tuple[str, str]] | None = None,
) -> tuple[list[Finding], int]:
    """Validate one parsed JSON document and return findings plus event count."""

    builder = _Builder(file=file, record=record, line=line)
    keys = seen_keys if seen_keys is not None else set()
    if isinstance(document, dict):
        _validate_event(document, builder, "$", keys)
        return builder.findings or [], 1
    if isinstance(document, list):
        for index, item in enumerate(document):
            _validate_event(item, builder, f"$[{index}]", keys)
        return builder.findings or [], len(document)
    builder.add("CE001", "error", "document must be a CloudEvent object or JSON batch array", "$")
    return builder.findings or [], 0


def parse_error_finding(
    message: str,
    *,
    file: str,
    record: int | None = None,
    line: int | None = None,
    column: int | None = None,
) -> Finding:
    return Finding(
        code="CE000",
        severity="error",
        message=message,
        file=file,
        path="$",
        line=line,
        column=column,
        record=record,
    )


def lint_json_text(
    text: str,
    *,
    file: str = "<input>",
    input_format: str = "json",
) -> tuple[list[Finding], int, int]:
    """Validate strict JSON or JSONL text.

    Returns ``(findings, events_checked, input_error_count)``. JSONL record and
    physical line numbers are one-based for editor and CI friendliness.
    """

    if input_format not in {"json", "jsonl"}:
        raise ValueError("input_format must be 'json' or 'jsonl'")
    findings: list[Finding] = []
    events_checked = 0
    input_errors = 0
    seen_keys: set[tuple[str, str]] = set()
    if input_format == "json":
        try:
            document = parse_json(text)
        except DuplicateMemberError as exc:
            findings.append(parse_error_finding(str(exc), file=file))
            return findings, 0, 1
        except InvalidConstantError as exc:
            findings.append(parse_error_finding(str(exc), file=file))
            return findings, 0, 1
        except json.JSONDecodeError as exc:
            findings.append(
                parse_error_finding(
                    f"invalid JSON: {exc.msg}",
                    file=file,
                    line=exc.lineno,
                    column=exc.colno,
                )
            )
            return findings, 0, 1
        document_findings, count = lint_document(
            document,
            file=file,
            seen_keys=seen_keys,
        )
        return document_findings, count, 0

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        record = line_number
        try:
            document = parse_json(raw_line)
        except DuplicateMemberError as exc:
            findings.append(
                parse_error_finding(str(exc), file=file, record=record, line=line_number)
            )
            input_errors += 1
            continue
        except InvalidConstantError as exc:
            findings.append(
                parse_error_finding(str(exc), file=file, record=record, line=line_number)
            )
            input_errors += 1
            continue
        except json.JSONDecodeError as exc:
            findings.append(
                parse_error_finding(
                    f"invalid JSON: {exc.msg}",
                    file=file,
                    record=record,
                    line=line_number,
                    column=exc.colno,
                )
            )
            input_errors += 1
            continue
        document_findings, count = lint_document(
            document,
            file=file,
            record=record,
            line=line_number,
            seen_keys=seen_keys,
        )
        findings.extend(document_findings)
        events_checked += count
    return findings, events_checked, input_errors


def rule_description(code: str) -> str:
    """Return the short SARIF description for a finding code."""

    return RULE_DESCRIPTIONS.get(code, "CloudEvents validation finding")
