"""CloudEvents v1.0.2 rules shared by the validator and renderers."""

from __future__ import annotations

import base64
import binascii
import re
from datetime import datetime
from urllib.parse import urlsplit

REQUIRED_ATTRIBUTES = ("id", "source", "specversion", "type")
OPTIONAL_ATTRIBUTES = ("datacontenttype", "dataschema", "subject", "time")
KNOWN_ATTRIBUTES = frozenset((*REQUIRED_ATTRIBUTES, *OPTIONAL_ATTRIBUTES))
SPECIAL_MEMBERS = frozenset(("data", "data_base64"))
ATTRIBUTE_NAME_RE = re.compile(r"^[a-z0-9]+$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
MEDIA_TYPE_RE = re.compile(
    r"^\s*([!#$%&'*+\-.^_`|~0-9A-Za-z]+)/([!#$%&'*+\-.^_`|~0-9A-Za-z]+)"
    r"(?:\s*;\s*[!#$%&'*+\-.^_`|~0-9A-Za-z]+="
    r"(?:[!#$%&'*+\-.^_`|~0-9A-Za-z]+|\"[^\"\\\r\n]*(?:\\.[^\"\\\r\n]*)*\"))*\s*$"
)
INTEGER_MIN = -(2**31)
INTEGER_MAX = 2**31 - 1

# Short descriptions are embedded in SARIF so code scanning UIs remain useful.
RULE_DESCRIPTIONS: dict[str, str] = {
    "CE000": "Input could not be read or parsed",
    "CE001": "Document must be a CloudEvent object or batch array",
    "CE002": "Batch member must be a CloudEvent object",
    "CE100": "Required CloudEvents attribute is missing",
    "CE101": "Required CloudEvents attribute has the wrong type",
    "CE102": "Required or non-null attribute must not be empty",
    "CE110": "CloudEvents specversion must be 1.0",
    "CE120": "Attribute name is not lower-case ASCII letters or digits",
    "CE121": "Attribute name is longer than the recommended 20 characters",
    "CE130": "Attribute string contains a disallowed Unicode character",
    "CE140": "source must be a non-empty URI-reference",
    "CE141": "dataschema must be a non-empty absolute URI",
    "CE150": "time must be an RFC 3339 timestamp",
    "CE160": "datacontenttype must be a valid media type",
    "CE170": "Extension attribute has an invalid CloudEvents type",
    "CE180": "data and data_base64 are mutually exclusive",
    "CE181": "data_base64 must be canonical base64 text",
    "CE182": "Non-JSON data must be represented as a string",
    "CE300": "source and id are duplicated in one input document",
}


def string_issue(value: str) -> str | None:
    """Return a reason when *value* violates CloudEvents string rules."""

    index = 0
    while index < len(value):
        codepoint = ord(value[index])
        if codepoint <= 0x1F or 0x7F <= codepoint <= 0x9F:
            return "contains a control character"
        if 0xFDD0 <= codepoint <= 0xFDEF or codepoint & 0xFFFF in (0xFFFE, 0xFFFF):
            return "contains a Unicode noncharacter"
        if 0xD800 <= codepoint <= 0xDBFF:
            if index + 1 < len(value) and 0xDC00 <= ord(value[index + 1]) <= 0xDFFF:
                index += 2
                continue
            return "contains an unpaired surrogate"
        if 0xDC00 <= codepoint <= 0xDFFF:
            return "contains an unpaired surrogate"
        index += 1
    return None


def valid_uri_reference(value: str) -> bool:
    """Perform conservative RFC 3986 URI-reference validation."""

    if not value or any(char.isspace() for char in value):
        return False
    if any(
        ord(char) > 0x7F or ord(char) < 0x20 or ord(char) == 0x7F or char in '\\<>"{}|^`'
        for char in value
    ):
        return False
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        return False
    try:
        urlsplit(value)
    except ValueError:
        return False
    return True


def valid_absolute_uri(value: str) -> bool:
    """Return whether *value* is a URI (not merely a relative reference)."""

    if not valid_uri_reference(value):
        return False
    try:
        return bool(urlsplit(value).scheme)
    except ValueError:
        return False


def valid_timestamp(value: str) -> bool:
    """Validate the RFC 3339 subset representable by :mod:`datetime`."""

    if not TIMESTAMP_RE.fullmatch(value):
        return False
    offset = value[-6:] if value[-1] != "Z" else None
    if offset is not None and (int(offset[:3]) > 23 or int(offset[4:]) > 59):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return True


def valid_media_type(value: str) -> bool:
    return bool(MEDIA_TYPE_RE.fullmatch(value))


def media_type_is_json(value: str | None) -> bool:
    if value is None:
        return True
    main_type = value.split(";", 1)[0].strip().lower()
    if "/" not in main_type:
        return False
    subtype = main_type.split("/", 1)[1]
    return subtype == "json" or subtype.endswith("+json")


def valid_base64(value: str) -> bool:
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error):
        return False
    return base64.b64encode(decoded).decode("ascii") == value


def valid_attribute_scalar(value: object) -> bool:
    """Check the JSON mappings allowed for an extension context attribute."""

    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, int):
        return INTEGER_MIN <= value <= INTEGER_MAX
    if isinstance(value, str):
        return string_issue(value) is None
    return False
