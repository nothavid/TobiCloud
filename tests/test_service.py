from pathlib import Path

from tobicloud.encoding import sha256_hex
from tobicloud.files import load_file_as_payload
from tobicloud.header import Header, decode_header, encode_header
from tobicloud.service import TobiCloudService, alias_key, segment_key


class MemoryStorage:
    def __init__(self) -> None:
        self.values: dict[str, list[str]] = {}

    def get(self, key: str) -> str | None:
        values = self.values.get(key, [])
        return values[-1] if values else None

    def set(self, key: str, value: str) -> None:
        self.values.setdefault(key, []).append(value)


def test_upload_and_download_plain_file(tmp_path: Path):
    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text("hello from tobicloud")
    storage = MemoryStorage()
    service = TobiCloudService(storage)

    upload = service.upload(source, alias="greeting")
    download = service.download("greeting", target)

    assert upload.file_hash == download.file_hash
    assert storage.get(alias_key("greeting")) == upload.file_hash
    assert target.read_text() == "hello from tobicloud"


def test_upload_and_download_encrypted_file(tmp_path: Path):
    source = tmp_path / "source.bin"
    target = tmp_path / "target.bin"
    source.write_bytes(b"\x00\x01top secret")
    service = TobiCloudService(MemoryStorage())

    upload = service.upload(source, password="pw")
    service.download(upload.file_hash, target, password="pw")

    assert target.read_bytes() == b"\x00\x01top secret"


def test_upload_reports_segment_progress(tmp_path: Path):
    source = tmp_path / "large.txt"
    source.write_text("a" * 700)
    service = TobiCloudService(MemoryStorage())
    updates: list[tuple[int, int]] = []

    upload = service.upload(source, progress=lambda current, total: updates.append((current, total)))

    assert upload.segment_count == 2
    assert updates == [(1, 2), (2, 2)]


def test_download_reports_segment_progress(tmp_path: Path):
    source = tmp_path / "large.txt"
    target = tmp_path / "target.txt"
    source.write_text("a" * 700)
    service = TobiCloudService(MemoryStorage())
    upload = service.upload(source)
    updates: list[tuple[int, int]] = []

    service.download(upload.file_hash, target, progress=lambda current, total: updates.append((current, total)))

    assert updates == [(1, 2), (2, 2)]


def test_segment_collisions_are_skipped(tmp_path: Path):
    source = tmp_path / "large.txt"
    source.write_text("a" * 700)
    storage = MemoryStorage()
    service = TobiCloudService(storage)

    payload = load_file_as_payload(source)
    file_hash = sha256_hex(payload)
    storage.set(segment_key(file_hash, 0), "occupied")

    upload = service.upload(source)

    assert upload.skipped == [0]
    assert storage.get(segment_key(upload.file_hash, 0)) == "occupied"
    assert storage.get(segment_key(upload.file_hash, 1)) is not None


def test_header_collision_rehashes_invalid_key(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("content")
    storage = MemoryStorage()
    service = TobiCloudService(storage)

    file_hash = sha256_hex("Y29udGVudA")
    first_header_key = sha256_hex(file_hash)
    storage.set(first_header_key, "invalid")

    upload = service.upload(source)

    assert upload.header_key == sha256_hex(first_header_key)
    assert decode_header(storage.get(upload.header_key)).length == 1


def test_existing_valid_header_is_treated_as_already_uploaded(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("content")
    storage = MemoryStorage()
    service = TobiCloudService(storage)

    file_hash = sha256_hex("Y29udGVudA")
    header_key = sha256_hex(file_hash)
    storage.set(header_key, encode_header(Header(alias=None, encrypted=False, length=1, skipped=[])))

    upload = service.upload(source, alias="same")

    assert upload.already_uploaded is True
    assert storage.get(alias_key("same")) == file_hash
