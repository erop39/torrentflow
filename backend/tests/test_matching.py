from app.matching import match_rule
from app.models import Rule


def test_first_enabled_matching_rule_wins() -> None:
    first = Rule(id=1, name="Linux", include_keywords="ubuntu,debian", priority=10, enabled=True)
    second = Rule(id=2, name="Fallback", include_keywords="", priority=20, enabled=True)
    assert match_rule("Ubuntu 24.04 release", [first, second]) is first


def test_matching_skips_disabled_rules_and_enforces_seed_threshold() -> None:
    disabled = Rule(id=1, name="Disabled", include_keywords="ubuntu", priority=1, enabled=False)
    needs_seeds = Rule(id=2, name="Seeded", include_keywords="ubuntu", priority=2, min_seeds=10, enabled=True)
    fallback = Rule(id=3, name="Fallback", include_keywords="ubuntu", priority=3, enabled=True)

    assert match_rule("Ubuntu 24.04", 9, [disabled, needs_seeds, fallback]) is fallback
    assert match_rule("Ubuntu 24.04", 10, [disabled, needs_seeds, fallback]) is needs_seeds


def test_matching_normalizes_case_whitespace_and_uses_keywords_as_or() -> None:
    rule = Rule(id=1, name="OS", include_keywords="  UBUNTU,  debian  ,", enabled=True)

    assert match_rule("New Debian image", 0, [rule]) is rule
    assert match_rule("Fedora image", 0, [rule]) is None


def test_empty_keyword_rule_matches_any_title_after_prior_rules_do_not_match() -> None:
    specific = Rule(id=1, name="Specific", include_keywords="ubuntu", enabled=True)
    catch_all = Rule(id=2, name="Catch all", include_keywords="", enabled=True)

    assert match_rule("Arch Linux image", 0, [specific, catch_all]) is catch_all
