# Security policy

## Reporting a vulnerability

Please do not include private event payloads in a public issue. Use GitHub's
private vulnerability reporting for this repository when available, or email
the maintainer listed in the repository profile with a minimal reproduction.

`cloudevent-lint` is designed to run offline. It does not make network requests,
send telemetry, or print the `data`/`data_base64` contents of an event. Keep that
property in mind when integrating it into CI logs.

## Input safety

The CLI rejects duplicate JSON object members, non-standard JSON constants, and
inputs larger than 16 MiB by default. Use `--max-bytes` only when a larger local
fixture is trusted and required.
