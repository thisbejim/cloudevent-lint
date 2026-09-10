# Opportunity research

Research was completed before implementation on 11 September 2026. The project
uses the CloudEvents JSON format as its normative scope; links below are primary
specification or project sources where possible.

## Evidence and candidate comparison

| Candidate | Pain / audience | Existing coverage | Decision |
| --- | --- | --- | --- |
| **CloudEvents JSON contract linting** | CNCF-graduated standard with SDKs and broad adopters; fixture and batch failures are costly because they appear at broker/consumer boundaries. | SDKs are runtime libraries; the archived [CNCF conformance tool](https://github.com/cloudevents/conformance) sends/listens over HTTP and is marked WIP. The [EU validator](https://www.itb.ec.europa.eu/json/cloudevents/upload) is hosted/upload-based. No focused, dependency-free local CI linter was found. | **Build.** High protocol clarity, low implementation risk, private/offline workflow, and a clear gap between SDKs and repository checks. |
| JSON-RPC 2.0 transcript linting | Common in wallets, infrastructure, and language servers; batch/notification correlation is subtle. | The [official JSON-RPC specification](https://www.jsonrpc.org/specification) is stable, and active hosted toolkits advertise validators; mature protocol libraries already expose request/response validation. | Reject: better-covered and less differentiated for a new standalone repository. |
| HAR/support artifact sanitization | Support engineers frequently need to share browser captures without cookies or PII. | [Google's har-sanitizer](https://github.com/google/har-sanitizer) and [Cloudflare's har-sanitizer](https://github.com/cloudflare/har-sanitizer) exist, alongside active capture/redaction tools; the problem is real but the space is crowded. | Reject: meaningful privacy work would require a larger redaction policy surface and overlaps existing local projects. |
| SAML metadata/certificate linting | Expiring signing certificates and metadata rollover cause enterprise outages. | Hosted monitoring such as [saml.watch](https://saml.watch/) and several vendor-specific test/metadata projects already cover the most visible workflows; generic XML security parsing raises scope and dependency risk. | Reject: niche first-release audience and higher parser/security burden. |

## Normative scope

The [CloudEvents core specification v1.0.2](https://github.com/cloudevents/spec/blob/ce%40v1.0.2/cloudevents/spec.md)
requires non-empty `id`, `source`, `specversion`, and `type` attributes. It
defines lower-case ASCII attribute names, scalar context types, URI references,
RFC 3339 timestamps, and a signed 32-bit integer range. The [JSON Event Format](https://github.com/cloudevents/spec/blob/ce%40v1.0.2/cloudevents/formats/json-format.md)
maps events to top-level JSON objects, reserves `data_base64` for base64 binary
payloads, makes `data`/`data_base64` mutually exclusive, and defines a JSON Batch
as an array (including a valid empty array).

## Scoring (1 low – 10 high)

| Dimension | Score | Reason |
| --- | ---: | --- |
| Pain / frequency | 8 | Contract errors surface only after transport and are difficult to diagnose. |
| Audience / demand | 8 | CNCF ecosystem spans cloud, serverless, brokers, and SDKs. |
| Dissatisfaction | 8 | Existing choices are runtime SDKs, hosted validation, or an archived conformance utility. |
| Improvement / time saved | 9 | A one-command pre-commit/CI gate replaces repeated manual payload inspection. |
| Open-source advantage | 9 | Offline, inspectable rules are important for private event payloads. |
| Discoverability | 8 | “CloudEvents linter” is a direct search phrase for contract authors. |
| Feasibility | 9 | JSON and RFC checks fit the Python standard library. |
| Maintainability | 8 | Stable v1.0.2 rules with explicit rule IDs and focused fixtures. |
| Standalone fit | 10 | One executable and library, no account, service, broker, or credentials. |

## Risks and mitigations

- **Spec interpretation drift:** pin the first release to CloudEvents v1.0.2 and
  link each rule to the relevant specification section.
- **False positives for extensions:** enforce only the shared CloudEvents type
  system; unknown extension semantics remain the producer's responsibility.
- **Payload leakage:** render metadata and paths only, never event data; all
  validation is local and network-free.
- **Large or hostile input:** reject oversized documents by a configurable byte
  limit, reject duplicate JSON members, and reject non-standard JSON constants.
