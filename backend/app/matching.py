from .models import Rule


def _normalized_csv(value: str | None) -> set[str]:
    return {item.strip().casefold() for item in (value or "").split(",") if item.strip()}


def _non_negative_int(value: object, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return default
    try:
        result = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return result if result >= 0 else default


def _rule_order_key(rule: Rule) -> tuple[int, int]:
    return (_non_negative_int(rule.priority, 100) or 0, _non_negative_int(rule.id, 0) or 0)


def match_rule(
    title: str,
    seeds: int | list[Rule],
    rules: list[Rule] | None = None,
    *,
    freeleech: bool = False,
    double_upload: bool = False,
    size_bytes: int | None = None,
    uploader: str | None = None,
) -> Rule | None:
    """Return the first enabled rule that matches release metadata.

    The two-argument ``match_rule(title, rules)`` form remains supported for
    callers that only have a title. Rules are sorted here as a final guard so
    every caller gets the same priority-then-id outcome.
    """
    if rules is None:
        rules = seeds  # type: ignore[assignment]
        seeds = 0
    normalized = str(title).casefold()
    actual_seeds = _non_negative_int(seeds, 0) or 0
    actual_size = _non_negative_int(size_bytes)
    normalized_uploader = uploader.strip().casefold() if isinstance(uploader, str) else ""
    for rule in sorted(rules, key=_rule_order_key):
        # SQLAlchemy applies column defaults on INSERT, so a newly constructed
        # Rule can still hold ``None`` here. Treat only an explicit False as
        # disabled; persisted rows always contain a boolean.
        if rule.enabled is False:
            continue
        if actual_seeds < (_non_negative_int(rule.min_seeds, 0) or 0):
            continue
        if bool(rule.freeleech_only) and freeleech is not True:
            continue
        if bool(rule.double_upload_only) and double_upload is not True:
            continue
        max_size = _non_negative_int(rule.max_size_bytes)
        if max_size is not None and (actual_size is None or actual_size > max_size):
            continue
        whitelist = _normalized_csv(rule.uploader_whitelist)
        blacklist = _normalized_csv(rule.uploader_blacklist)
        if normalized_uploader and normalized_uploader in blacklist:
            continue
        if whitelist and normalized_uploader not in whitelist:
            continue
        keywords = _normalized_csv(rule.include_keywords)
        if not keywords or any(keyword in normalized for keyword in keywords):
            return rule
    return None
