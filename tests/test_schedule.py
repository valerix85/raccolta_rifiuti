"""Unit tests for the rule syntax."""
from datetime import date, timedelta

import pytest

from custom_components.raccolta_rifiuti.schedule import (
    RuleError,
    apply_exception,
    build_schedule,
    describe_rule,
    parse_rule,
    rule_matches,
)


def days(rule, start=date(2026, 10, 1), n=70):
    toks = parse_rule(rule)
    return [start + timedelta(d) for d in range(n) if rule_matches(toks, start + timedelta(d))]


def test_weekly_and_names():
    assert [d.weekday() for d in days("lun, Venerdì", n=7)] == [4, 0]
    assert days("MON,fri", n=14) == days("lun,ven", n=14)


def test_parity_matches_strftime_W():
    odd = days("-mar")
    even = days("--mar")
    assert all(int(d.strftime("%W")) % 2 == 1 for d in odd)
    assert all(int(d.strftime("%W")) % 2 == 0 for d in even)
    assert sorted(odd + even) == days("mar")


def test_cycle():
    d = days("2|1|mer")
    assert all(b - a == timedelta(days=14) for a, b in zip(d, d[1:], strict=False))
    # anchored on 30/11/2020: wednesday 2/12/2020 is week 1
    assert rule_matches(parse_rule("2|1|mer"), date(2020, 12, 2))
    assert not rule_matches(parse_rule("2|2|mer"), date(2020, 12, 2))
    assert rule_matches(parse_rule("4 | 3 | lun"), date(2020, 12, 14))


def test_nth_and_dates():
    assert days("lun#1", n=40) == [date(2026, 10, 5), date(2026, 11, 2)]
    assert days("ven#ult", n=40) == [date(2026, 10, 30)]
    assert rule_matches(parse_rule("25/12"), date(2031, 12, 25))
    assert days("27/12/2026", start=date(2026, 12, 1), n=40) == [date(2026, 12, 27)]
    assert days("2026-12-27", start=date(2026, 12, 1), n=40) == [date(2026, 12, 27)]


@pytest.mark.parametrize("bad", ["lunedx", "9|1|lun", "2|3|lun", "lun#7", "31/02", "-xyz"])
def test_invalid(bad):
    with pytest.raises(RuleError):
        parse_rule(bad)


def test_empty_rule_never():
    assert parse_rule("") == [] and parse_rule("  ") == []


def test_build_and_exceptions():
    rules = {"organic": parse_rule("lun,ven"), "paper": parse_rule("lun")}
    sched = build_schedule(rules, date(2026, 10, 5), 7)
    assert sched == {date(2026, 10, 5): ["organic", "paper"], date(2026, 10, 9): ["organic"]}
    assert apply_exception(["organic", "paper"], ["organic"], True, []) == ["paper"]
    assert apply_exception(["organic", "paper"], [], True, []) == []
    assert apply_exception(["paper"], ["glass"], False, []) == ["paper", "glass"]


def test_describe():
    assert describe_rule(parse_rule("lun,-mar,2|1|mer,lun#ult,25/12")) == (
        "ogni lun, mar settimane dispari, mer settimana 1 di 2, ultimo lun del mese, ogni 25/12"
    )
