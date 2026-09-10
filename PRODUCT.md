# Product specification: cloudevent-lint

## Target user

Developers and platform teams that publish or consume CloudEvents and keep event
fixtures, examples, contract tests, or captured payloads in a repository.

## Problem

CloudEvents interoperability failures are often found only after an event crosses
a broker or reaches another SDK. A library can validate while an application is
running, but repositories still need a small, deterministic check that can run in
pre-commit and CI against JSON fixtures and batches. Hosted validators are awkward
for private payloads and do not give a stable local exit code or path-aware diff.

## Existing alternatives

- CloudEvents SDKs validate as part of application code and transport handling.
- The CNCF conformance repository provides a Go sender/listener workflow, but is
  archived and is aimed at exercising receivers over HTTP.
- The European Commission Interoperability Test Bed provides a hosted JSON
  validator and API, which requires sending the document to a service.
- Generic JSON Schema validators can validate a schema, but do not explain
  CloudEvents batch/extension/data semantics or provide a fixture-oriented CLI.

## Core use case

Run `cloudevent-lint examples/` locally or in CI. The command finds JSON and JSONL
fixtures, validates required and optional context attributes, extension values,
JSON data encoding, base64 data, and batch contents, then emits human-readable,
JSON, or SARIF findings. A non-zero status makes malformed contracts block a
build without exposing event payloads in the report.

## Non-goals for v1

- Sending events, starting a broker, or making network requests.
- Validating application-specific payload schemas (use a JSON Schema validator
  separately; `dataschema` is checked only as a URI).
- Implementing every CloudEvents protocol binding (HTTP binary mode, Kafka,
  AMQP, and others are future work).
- Replacing a language SDK or generating producers/consumers.

## Interface

```text
cloudevent-lint [OPTIONS] PATH [PATH ...]
```

`PATH` may be a JSON/JSONL file, a directory (recursively scanning `.json`,
`.jsonl`, and `.ndjson`), or `-` for stdin. `--input-format` can force JSON or
JSONL when a filename is ambiguous. `--format text|json|sarif` selects output;
`--strict` treats warnings as failures; `--max-bytes` bounds each input.

## Inputs and outputs

- JSON object: one structured CloudEvent.
- JSON array: a CloudEvents JSON batch; an empty batch is valid.
- JSONL/NDJSON: one object or batch per non-empty line.
- Text output contains file, JSON path, rule code, severity, and a summary; it
  never echoes `data` values.
- JSON and SARIF output contain the same finding metadata for CI integrations.

## Errors and exit status

- `0`: all documents are valid (and have no warnings when `--strict` is used).
- `1`: one or more CloudEvents validation findings fail the selected threshold.
- `2`: an input cannot be read/parsed, a directory has no supported documents, or
  command-line arguments are invalid.

## Architecture

The implementation is a Python standard-library package. A duplicate-key-aware
JSON loader feeds a pure validator. Rule functions add immutable findings with
JSON paths; the CLI aggregates files and renders text, JSON, or SARIF. No network
or telemetry code is present.

## Validation plan

Tests cover valid events, optional/null attributes, JSON and binary data, batches,
JSONL, duplicate keys, malformed JSON, unsupported types, URI/timestamp/media
type errors, control characters, duplicate source/id pairs, directory scanning,
stdin, all renderers, warning strictness, input limits, and CLI exit codes.

## Differentiator

`cloudevent-lint` is intentionally a local contract gate rather than a runtime
SDK or hosted demo: it understands the JSON Event and Batch formats, reports
stable rule IDs at JSON paths, supports SARIF/CI, and avoids transmitting or
printing event data.
