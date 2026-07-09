"""High-level upload and download workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .encoding import sha256_hex
from .files import decode_payload, load_file_as_payload, write_file
from .header import Header, decode_header, encode_header
from .storage import Storage

# The original protocol says 512 characters, but the live API returns HTTP 500
# for text values above 500 characters.
SEGMENT_SIZE = 500
HEADER_SIZE_LIMIT = 500
ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class UploadResult:
    file_hash: str
    header_key: str
    already_uploaded: bool
    alias: str | None
    segment_count: int
    skipped: list[int]


@dataclass(frozen=True)
class DownloadResult:
    file_hash: str
    header: Header
    path: Path


class TobiCloudService:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def upload(
        self,
        path: Path,
        password: str | None = None,
        alias: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> UploadResult:
        payload = load_file_as_payload(path, password)
        file_hash = sha256_hex(payload)
        header_key, existing_header = self._resolve_header_key(file_hash)

        if existing_header is not None:
            if alias is not None:
                self._store_alias(alias, file_hash)
            return UploadResult(
                file_hash=file_hash,
                header_key=header_key,
                already_uploaded=True,
                alias=alias,
                segment_count=existing_header.length,
                skipped=existing_header.skipped,
            )

        segments = _split_payload(payload)
        skipped = self._store_segments(file_hash, segments, progress)
        header = Header(alias=alias, encrypted=password is not None, length=len(segments), skipped=skipped)
        encoded_header = encode_header(header)
        if len(encoded_header) > HEADER_SIZE_LIMIT:
            raise ValueError("Encoded header exceeds 500 characters")

        self.storage.set(header_key, encoded_header)
        if alias is not None:
            self._store_alias(alias, file_hash)

        return UploadResult(
            file_hash=file_hash,
            header_key=header_key,
            already_uploaded=False,
            alias=alias,
            segment_count=len(segments),
            skipped=skipped,
        )

    def download(
        self,
        hash_or_alias: str,
        download_path: Path,
        password: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> DownloadResult:
        file_hash = self.resolve_file_hash(hash_or_alias)
        _header_key, header = self._resolve_existing_header(file_hash)

        if header.encrypted and password is None:
            raise ValueError("A password is required to decrypt this file")

        payload = self._load_payload(file_hash, header, progress)
        data = decode_payload(payload, password if header.encrypted else None)
        write_file(download_path, data)
        return DownloadResult(file_hash=file_hash, header=header, path=download_path)

    def resolve_file_hash(self, hash_or_alias: str) -> str:
        alias_value = self.storage.get(alias_key(hash_or_alias))
        return alias_value if alias_value is not None else hash_or_alias

    def _store_alias(self, alias: str, file_hash: str) -> None:
        self.storage.set(alias_key(alias), file_hash)

    def _resolve_header_key(self, file_hash: str) -> tuple[str, Header | None]:
        header_key = sha256_hex(file_hash)
        while True:
            value = self.storage.get(header_key)
            if value is None:
                return header_key, None
            try:
                return header_key, decode_header(value)
            except ValueError:
                header_key = sha256_hex(header_key)

    def _resolve_existing_header(self, file_hash: str) -> tuple[str, Header]:
        header_key = sha256_hex(file_hash)
        while True:
            value = self.storage.get(header_key)
            if value is None:
                raise KeyError(f"No file found for hash {file_hash}")
            try:
                return header_key, decode_header(value)
            except ValueError:
                header_key = sha256_hex(header_key)

    def _store_segments(
        self,
        file_hash: str,
        segments: list[str],
        progress: ProgressCallback | None = None,
    ) -> list[int]:
        skipped: list[int] = []
        index = 0
        for stored_count, segment in enumerate(segments, start=1):
            while True:
                key = segment_key(file_hash, index)
                if self.storage.get(key) is None:
                    self.storage.set(key, segment)
                    _report_progress(progress, stored_count, len(segments))
                    index += 1
                    break

                skipped.append(index)
                index += 1
        return skipped

    def _load_payload(
        self,
        file_hash: str,
        header: Header,
        progress: ProgressCallback | None = None,
    ) -> str:
        skipped = set(header.skipped)
        collected: list[str] = []
        index = 0
        while len(collected) < header.length:
            if index in skipped:
                index += 1
                continue

            value = self.storage.get(segment_key(file_hash, index))
            if value is None:
                raise KeyError(f"Missing segment {index} for hash {file_hash}")

            collected.append(value)
            _report_progress(progress, len(collected), header.length)
            index += 1

        return "".join(collected)


def alias_key(alias: str) -> str:
    return f"a:{sha256_hex(alias)}"


def segment_key(file_hash: str, index: int) -> str:
    return sha256_hex(f"{file_hash}-{index}")


def _split_payload(payload: str) -> list[str]:
    if payload == "":
        return []
    return [payload[index : index + SEGMENT_SIZE] for index in range(0, len(payload), SEGMENT_SIZE)]


def _report_progress(progress: ProgressCallback | None, current: int, total: int) -> None:
    if progress is not None:
        progress(current, total)
