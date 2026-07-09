"""Remote key-value storage adapter."""

from __future__ import annotations

from typing import Protocol

import requests


LIST_URL = "http://webtechlecture.appspot.com/chat/posting/list"
NEW_URL = "http://webtechlecture.appspot.com/chat/posting/new"


class Storage(Protocol):
    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str) -> None:
        ...


class HttpStorage:
    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def get(self, key: str) -> str | None:
        response = requests.get(LIST_URL, params={"userid": key}, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        entries = data.get("result") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise RuntimeError("Storage API returned a non-list response")

        texts = [entry["text"] for entry in entries if isinstance(entry, dict) and "text" in entry]
        if not texts:
            return None
        return str(texts[-1])

    def set(self, key: str, value: str) -> None:
        response = requests.get(
            NEW_URL,
            params={"userid": key, "text": value},
            timeout=self.timeout,
        )
        response.raise_for_status()
