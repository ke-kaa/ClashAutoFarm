"""Tests for utils.notifier — Telegram delivery, dedupe, and error handling."""

from utils.notifier import NullNotifier, TelegramNotifier


def _notifier(**kw):
    return TelegramNotifier("token", "chat", async_send=False, **kw)


def test_null_notifier_is_noop():
    NullNotifier().send("anything", image_path="x", key="k")


def test_send_text_posts_message(monkeypatch):
    sent = []
    n = _notifier()
    monkeypatch.setattr(n, "_post_message", lambda text: sent.append(text))
    n.send("hello")
    assert sent == ["hello"]


def test_send_with_image_posts_photo(monkeypatch):
    sent = []
    n = _notifier()
    monkeypatch.setattr(n, "_post_photo", lambda text, path: sent.append((text, path)))
    n.send("caption", image_path="shot.png")
    assert sent == [("caption", "shot.png")]


def test_dedupe_by_key_within_cooldown(monkeypatch):
    count = []
    n = _notifier(cooldown=999)
    monkeypatch.setattr(n, "_post_message", lambda text: count.append(text))
    n.send("first", key="dc")
    n.send("second", key="dc")
    assert count == ["first"]


def test_no_key_always_sends(monkeypatch):
    count = []
    n = _notifier(cooldown=999)
    monkeypatch.setattr(n, "_post_message", lambda text: count.append(text))
    n.send("a")
    n.send("b")
    assert count == ["a", "b"]


def test_delivery_error_is_swallowed(monkeypatch):
    n = _notifier()

    def boom(text):
        raise RuntimeError("network down")

    monkeypatch.setattr(n, "_post_message", boom)
    n.send("hello")  # must not raise
