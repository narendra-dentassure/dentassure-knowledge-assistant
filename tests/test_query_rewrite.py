"""Query rewrite tests."""

from src.application.query_rewrite import expand_query


def test_denssure_typo_expands_to_dentassure() -> None:
    expanded = expand_query("how to take denssure plan which is best plan ?")
    lowered = expanded.lower()
    assert "dentassure" in lowered
    assert "enroll" in lowered or "buy" in lowered
    assert "care" in lowered
