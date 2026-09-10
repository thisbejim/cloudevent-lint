from __future__ import annotations

import json

from cloudevent_lint import lint_document, lint_json_text


def event(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "specversion": "1.0",
        "type": "com.example.created",
        "source": "/example",
        "id": "evt-1",
    }
    result.update(overrides)
    return result


def codes(findings: list[object]) -> set[str]:
    return {finding.code for finding in findings}  # type: ignore[attr-defined]


def test_valid_event_and_optional_nulls() -> None:
    findings, count = lint_document(
        event(
            time="2026-09-11T08:30:00Z",
            datacontenttype="application/json; charset=utf-8",
            dataschema="https://example.com/schema.json",
            subject=None,
            data={"ok": True},
            extension=True,
        )
    )
    assert findings == []
    assert count == 1


def test_required_attributes_are_checked() -> None:
    findings, count = lint_document({"specversion": "1.0", "type": ""})
    assert count == 1
    assert {"CE100", "CE102"}.issubset(codes(findings))


def test_specversion_source_and_required_types() -> None:
    findings, _ = lint_document(event(specversion="0.3", source="not a uri", id=5, type=None))
    assert {"CE101", "CE110", "CE140"}.issubset(codes(findings))


def test_optional_formats_and_context_values() -> None:
    findings, _ = lint_document(
        event(
            time="yesterday",
            dataschema="/relative.json",
            datacontenttype="nope",
            subject=3,
            extension=2**31,
            float_extension=1.5,
            BadName="x",
        )
    )
    assert {"CE120", "CE141", "CE150", "CE160", "CE170"}.issubset(codes(findings))


def test_string_and_uri_edge_cases() -> None:
    findings, _ = lint_document(
        event(
            id="bad\x01id",
            source="https://example.com/%zz",
            extension="bad\u007fvalue",
        )
    )
    assert "CE130" in codes(findings)
    assert "CE140" in codes(findings)


def test_rfc3339_and_base64_boundaries() -> None:
    valid, _ = lint_document(event(time="2026-02-28T23:59:59+23:59", data_base64=""))
    assert valid == []
    invalid, _ = lint_document(event(time="2026-02-29T23:59:60Z", data_base64="YQ"))
    assert {"CE150", "CE181"}.issubset(codes(invalid))


def test_data_and_binary_encoding_rules() -> None:
    findings, _ = lint_document(
        event(
            datacontenttype="application/xml",
            data={"not": "a string"},
            data_base64="%%%",
        )
    )
    assert {"CE180", "CE181", "CE182"}.issubset(codes(findings))


def test_empty_batch_is_valid_and_non_object_is_not() -> None:
    assert lint_document([]) == ([], 0)
    findings, count = lint_document([event(), 3])
    assert count == 2
    assert any(finding.code == "CE002" and finding.path == "$[1]" for finding in findings)


def test_duplicate_source_and_id_is_a_warning() -> None:
    duplicate = event()
    findings, _ = lint_document([duplicate, duplicate])
    assert [(finding.code, finding.severity) for finding in findings] == [("CE300", "warning")]


def test_duplicate_json_members_are_rejected() -> None:
    findings, count, input_errors = lint_json_text(
        '{"specversion":"1.0","specversion":"1.0","type":"x","source":"/x","id":"1"}',
        file="fixture.json",
    )
    assert count == 0
    assert input_errors == 1
    assert findings[0].code == "CE000"
    assert "specversion" in findings[0].message


def test_non_standard_json_constants_are_rejected() -> None:
    findings, _, input_errors = lint_json_text(
        '{"specversion":"1.0","type":"x","source":"/x","id":"1","data":NaN}'
    )
    assert input_errors == 1
    assert findings[0].code == "CE000"


def test_jsonl_tracks_records_and_continues_after_bad_line() -> None:
    text = "\n".join(
        [
            json.dumps(event(id="one")),
            "{not json}",
            json.dumps(event(id="two")),
        ]
    )
    findings, count, input_errors = lint_json_text(text, file="events.jsonl", input_format="jsonl")
    assert count == 2
    assert input_errors == 1
    assert any(
        finding.code == "CE000" and finding.record == 2 and finding.line == 2
        for finding in findings
    )


def test_jsonl_duplicate_is_detected_across_records() -> None:
    text = f"{json.dumps(event())}\n{json.dumps(event())}\n"
    findings, count, input_errors = lint_json_text(text, input_format="jsonl")
    assert count == 2
    assert input_errors == 0
    assert [(finding.code, finding.record) for finding in findings] == [("CE300", 2)]


def test_malformed_top_level_document() -> None:
    findings, count = lint_document("event")
    assert count == 0
    assert findings[0].code == "CE001"
