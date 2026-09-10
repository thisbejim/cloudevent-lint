# cloudevent-lint

[![CI](https://github.com/thisbejim/cloudevent-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/thisbejim/cloudevent-lint/actions/workflows/ci.yml)

Offline CloudEvents JSON contract linting for fixtures, captured events, and CI.
It validates CloudEvents v1.0.2 objects, JSON batches, and JSONL/NDJSON without
credentials, a broker, or a network connection.

## Why

An event can look fine inside a producer's SDK and still fail when another
consumer parses it. Required context attributes, extension types, timestamps,
URI values, and binary-vs-JSON data encoding are easy to get subtly wrong. A
repository needs a repeatable gate that explains exactly which JSON path is
wrong, while keeping private payloads out of CI logs.

`cloudevent-lint` complements (rather than replaces) a language SDK: it checks
stored contracts before they are deployed and emits stable rule IDs for CI.

## Install

Requires Python 3.10 or newer.

```bash
python -m pip install cloudevent-lint
```

For a checkout:

```bash
git clone https://github.com/thisbejim/cloudevent-lint.git
cd cloudevent-lint
python -m pip install -e '.[dev]'
```

The runtime package uses only the Python standard library.

## Quick start

```bash
cloudevent-lint examples/valid-event.json
```

```text
passed: 1 file(s), 1 event(s), 0 error(s), 0 warning(s)
```

Scan a fixture directory (JSON, JSONL, and NDJSON are found recursively):

```bash
cloudevent-lint fixtures/ --strict
```

Use stdin, JSON output, or SARIF for code-scanning integrations:

```bash
cat event.json | cloudevent-lint - --format json
cloudevent-lint fixtures/ --format sarif > cloudevent-lint.sarif
```

Validation findings never include the `data` payload. A failing command returns
status `1`; unreadable or malformed input returns status `2`.

## What is checked

- Required non-empty `id`, `source`, `specversion`, and `type` attributes.
- `specversion` exactly `1.0`, lower-case ASCII attribute names, and the
  CloudEvents scalar type system (including the signed 32-bit integer range).
- URI-reference `source`, absolute-URI `dataschema`, RFC 3339 `time`, and RFC
  2046 `datacontenttype` values.
- JSON Event Format `data`/`data_base64` exclusivity and canonical RFC 4648
  base64.
- Extension values, duplicate JSON members, JSONL records, empty batches, and
  repeated `source` + `id` pairs (as warnings).

The normative behavior comes from the [CloudEvents core specification v1.0.2](https://github.com/cloudevents/spec/blob/ce%40v1.0.2/cloudevents/spec.md)
and its [JSON Event Format](https://github.com/cloudevents/spec/blob/ce%40v1.0.2/cloudevents/formats/json-format.md).

## Command reference

```text
cloudevent-lint [OPTIONS] PATH [PATH ...]

Options:
  --input-format {auto,json,jsonl}  Infer from .jsonl/.ndjson unless forced
  --format {text,json,sarif}        Report format (default: text)
  --strict                          Treat warnings as failures
  --quiet                           Hide a clean text summary
  --max-bytes N                     Per-input limit (default: 16777216)
  --version                         Print the version
```

`PATH` can be a file, a directory, or `-` for stdin. An array is interpreted as
the CloudEvents JSON Batch Format; an empty array is valid. JSONL uses one-based
physical line numbers as record identifiers.

## Example failure

```json
{
  "specversion": "1.0",
  "type": "com.example.order.created",
  "source": "/orders",
  "id": "42",
  "time": "yesterday",
  "data": {"order": 42}
}
```

```bash
cloudevent-lint broken.json
```

```text
error: broken.json:$.time [CE150] time must be an RFC 3339 timestamp
failed: 1 file(s), 1 event(s), 1 error(s), 0 warning(s)
```

## Library API

```python
from cloudevent_lint import lint_json_text, scan_paths

document = '{"specversion":"1.0","type":"com.example.created","source":"/example","id":"evt-1"}'
findings, events, input_errors = lint_json_text(document)
report = scan_paths(["examples/"])
assert report.exit_code() == 0
```

`Finding.as_dict()` and `Report.as_dict()` are stable, payload-safe structures
for custom integrations. SARIF output is version 2.1.0.

## Rules

Rule IDs are intentionally stable so CI suppressions and dashboards do not need
to parse prose. `CE000` is an input error; `CE100`–`CE182` are event/format
checks; `CE300` warns about a repeated producer key. The full descriptions are
available in `cloudevent_lint.rules.RULE_DESCRIPTIONS` and the generated SARIF
report.

## Scope and privacy

This release validates stand-alone JSON events and batches. It does not send
events, implement transport bindings, fetch `dataschema` URLs, or validate
application-specific payload schemas. All processing is local, deterministic,
and telemetry-free. Inputs are capped at 16 MiB by default; raise the limit only
for trusted local fixtures.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

The project is released under the [MIT license](LICENSE). See
[CONTRIBUTING.md](CONTRIBUTING.md) for the development checklist and
[SECURITY.md](SECURITY.md) for input-safety notes.
