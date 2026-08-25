from .models import Rule


def match_rule(title: str, seeds: int | list[Rule], rules: list[Rule] | None = None) -> Rule | None:
    if rules is None:
        rules = seeds  # type: ignore[assignment]
        seeds = 0
    normalized = title.casefold()
    for rule in rules:
        if not rule.enabled:
            continue
        if int(seeds) < (rule.min_seeds or 0):
            continue
        keywords = [item.strip().casefold() for item in rule.include_keywords.split(",") if item.strip()]
        if not keywords or any(keyword in normalized for keyword in keywords):
            return rule
    return None
