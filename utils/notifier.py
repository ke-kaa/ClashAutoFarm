"""
utils/notifier.py — best-effort Telegram notifications.

NullNotifier is the default no-op so callers never need to branch on whether
notifications are enabled. TelegramNotifier delivers on a daemon thread and
swallows any error, so a notify failure can never disrupt the bot.
"""

import threading
import time
import urllib.parse
import urllib.request

from loguru import logger

_API = "https://api.telegram.org/bot{token}/{method}"
_BOUNDARY = "----ClashAutoFarmBoundary"
_TIMEOUT = 10


class NullNotifier:
    def send(self, text, image_path=None, key=None):
        pass


class TelegramNotifier:
    def __init__(self, token, chat_id, cooldown=60, async_send=True):
        self.token = token
        self.chat_id = str(chat_id)
        self.cooldown = cooldown
        self.async_send = async_send
        self._last_sent = {}
        self._lock = threading.Lock()

    def send(self, text, image_path=None, key=None):
        if not self._allow(key):
            return
        if self.async_send:
            threading.Thread(
                target=self._deliver, args=(text, image_path), daemon=True
            ).start()
        else:
            self._deliver(text, image_path)

    def _allow(self, key):
        if key is None:
            return True
        with self._lock:
            now = time.monotonic()
            last = self._last_sent.get(key)
            if last is not None and now - last < self.cooldown:
                return False
            self._last_sent[key] = now
            return True

    def _deliver(self, text, image_path):
        try:
            if image_path:
                self._post_photo(text, image_path)
            else:
                self._post_message(text)
        except Exception as e:
            logger.debug("Telegram notify failed: {}", e)

    def _post_message(self, text):
        url = _API.format(token=self.token, method="sendMessage")
        data = urllib.parse.urlencode({"chat_id": self.chat_id, "text": text}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=_TIMEOUT)

    def _post_photo(self, text, image_path):
        with open(image_path, "rb") as f:
            image = f.read()
        url = _API.format(token=self.token, method="sendPhoto")
        req = urllib.request.Request(url, data=self._multipart(image, caption=text))
        req.add_header("Content-Type", f"multipart/form-data; boundary={_BOUNDARY}")
        urllib.request.urlopen(req, timeout=_TIMEOUT)

    def _multipart(self, image, caption=""):
        b = _BOUNDARY
        parts = [
            f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{self.chat_id}\r\n",
            f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n",
            f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; "
            f"filename=\"screenshot.png\"\r\nContent-Type: image/png\r\n\r\n",
        ]
        body = "".join(parts).encode() + image + f"\r\n--{b}--\r\n".encode()
        return body
