"""Safe, configurable Telegram notification templates.

Only a deliberately small set of scalar placeholders is supported.  Templates
are configuration rather than credentials, but validation still happens before
they are persisted so a typo cannot stop RSS processing later.
"""

from __future__ import annotations

from string import Formatter
from typing import Mapping


TELEGRAM_MESSAGE_TEMPLATE_SETTING = "telegram_message_template"
DEFAULT_TELEGRAM_MESSAGE_TEMPLATE = "TorrentFlow: {title}\nRule: {rule}\nCategory: {category}"
TELEGRAM_TEMPLATE_PLACEHOLDERS = frozenset({"title", "rule", "category", "seeds", "feed", "link"})
MAX_TELEGRAM_TEMPLATE_LENGTH = 4096


class TelegramTemplateValidationError(ValueError):
    """Raised when a template is malformed or uses unsupported formatting."""


def validate_telegram_message_template(template: str) -> str:
    """Validate a bounded, plain-text template with whitelisted placeholders."""

    if not isinstance(template, str):
        raise TelegramTemplateValidationError("Telegram template must be text")
    if not template.strip():
        raise TelegramTemplateValidationError("Telegram template must not be empty")
    if len(template) > MAX_TELEGRAM_TEMPLATE_LENGTH:
        raise TelegramTemplateValidationError(
            f"Telegram template must not exceed {MAX_TELEGRAM_TEMPLATE_LENGTH} characters"
        )
    try:
        fields = list(Formatter().parse(template))
    except ValueError as error:
        raise TelegramTemplateValidationError("Telegram template contains unmatched braces") from error
    for _, field_name, format_spec, conversion in fields:
        if field_name is None:
            continue
        if field_name not in TELEGRAM_TEMPLATE_PLACEHOLDERS:
            supported = ", ".join(sorted(TELEGRAM_TEMPLATE_PLACEHOLDERS))
            raise TelegramTemplateValidationError(
                f"Unsupported Telegram template placeholder '{field_name}'. Supported: {supported}"
            )
        if format_spec or conversion:
            raise TelegramTemplateValidationError(
                "Telegram template placeholders do not support format specifiers or conversions"
            )
    return template


def render_telegram_message(template: str | None, values: Mapping[str, object]) -> str:
    """Render a configured template, falling back safely for legacy bad data."""

    try:
        selected = validate_telegram_message_template(template or DEFAULT_TELEGRAM_MESSAGE_TEMPLATE)
        return selected.format(**{key: str(values.get(key, "")) for key in TELEGRAM_TEMPLATE_PLACEHOLDERS})
    except (TelegramTemplateValidationError, KeyError, ValueError):
        return DEFAULT_TELEGRAM_MESSAGE_TEMPLATE.format(
            **{key: str(values.get(key, "")) for key in TELEGRAM_TEMPLATE_PLACEHOLDERS}
        )
