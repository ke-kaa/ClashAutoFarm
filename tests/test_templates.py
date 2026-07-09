"""Tests for vision.templates — verify each predicate looks up the right template key."""

import pytest

from vision import templates as tmpl

TEMPLATE_KEYS = {
    "wifi_disconnected",
    "reconnect_popup",
    "scout_screen",
    "home_screen",
    "battle_over",
    "claim_reward",
}


@pytest.fixture
def captured(monkeypatch):
    seen = {}

    def fake_find(screen, template=None, threshold=None):
        seen["template"] = template
        seen["threshold"] = threshold
        return True

    monkeypatch.setattr(tmpl, "find", fake_find)
    return seen


# tag every template with its own key so we can assert which one was selected
@pytest.fixture
def templates():
    return {k: k for k in TEMPLATE_KEYS}


@pytest.mark.parametrize("func,key", [
    ("is_disconnected", "wifi_disconnected"),
    ("is_reconnect_popup", "reconnect_popup"),
    ("is_onscout_screen", "scout_screen"),
    ("is_home_screen", "home_screen"),
    ("is_battle_over", "battle_over"),
    ("is_claim_reward", "claim_reward"),
])
def test_predicate_uses_expected_template(captured, templates, func, key):
    result = getattr(tmpl, func)("SCREEN", templates)
    assert result is True
    assert captured["template"] == key


def test_predicate_forwards_threshold(captured, templates):
    tmpl.is_onscout_screen("SCREEN", templates, threshold=0.75)
    assert captured["threshold"] == 0.75
