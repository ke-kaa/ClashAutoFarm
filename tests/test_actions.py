"""Tests for bot.actions — verify click/wait sequences without touching pyautogui."""

import pytest

from bot import actions


@pytest.fixture
def recorder(monkeypatch):
    calls = []
    monkeypatch.setattr(actions, "click", lambda *a, **k: calls.append(("click", a)))
    monkeypatch.setattr(actions, "wait", lambda s: calls.append(("wait", s)))
    monkeypatch.setattr(actions, "_random_delay", lambda *a, **k: None)
    return calls


def test_claim_treasure_reward_sequence(recorder):
    cfg = {
        "claim_button": [10, 20],
        "advanced_clicks": [[1, 1], [2, 2], [3, 3]],
        "final_click_delay": 4,
        "final_click": [99, 99],
    }
    actions.claim_treasure_reward(cfg)

    clicks = [c for c in recorder if c[0] == "click"]
    waits = [c for c in recorder if c[0] == "wait"]

    # 1 claim + 3 advance + 1 final = 5 clicks
    assert len(clicks) == 5
    assert clicks[0] == ("click", (10, 20))
    assert clicks[-1] == ("click", (99, 99))
    # final_click_delay passed as a scalar (regression guard for the wait(*...) bug)
    assert waits == [("wait", 4)]


def test_claim_reward_final_wait_before_final_click(recorder):
    cfg = {
        "claim_button": [0, 0],
        "advanced_clicks": [[1, 1]],
        "final_click_delay": 2,
        "final_click": [5, 5],
    }
    actions.claim_treasure_reward(cfg)

    # the wait must come immediately before the last click
    assert recorder[-2] == ("wait", 2)
    assert recorder[-1] == ("click", (5, 5))
