from app.matching import match_rule
from app.models import Rule


def test_first_enabled_matching_rule_wins() -> None:
    first = Rule(id=1, name="Linux", include_keywords="ubuntu,debian", priority=10, enabled=True)
    second = Rule(id=2, name="Fallback", include_keywords="", priority=20, enabled=True)
    assert match_rule("Ubuntu 24.04 release", [first, second]) is first
