"""Typer command-line interface for TobiCloud."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from .storage import HttpStorage
from .service import TobiCloudService

app = typer.Typer(help="Simple cloud storage backed by the webtechlecture key-value API.")


@app.command()
def upload(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    password: str | None = typer.Option(None, "-p", "--password", help="Encrypt the file with this password."),
    alias: str | None = typer.Option(None, "-a", "--alias", help="Alias to store for this file."),
) -> None:
    """Upload a local file."""
    service = TobiCloudService(HttpStorage())
    progress = SegmentProgressBar("Uploading")
    try:
        result = service.upload(path, password=password, alias=alias, progress=progress)
    except Exception as exc:
        raise typer.Exit(_error(str(exc))) from exc
    finally:
        progress.close()

    status = "already uploaded" if result.already_uploaded else "uploaded"
    typer.echo(f"File {status}.")
    typer.echo(f"hash: {result.file_hash}")
    typer.echo(f"header: {result.header_key}")
    typer.echo(f"segments: {result.segment_count}")
    if result.skipped:
        typer.echo(f"skipped: {','.join(str(item) for item in result.skipped)}")
    if result.alias:
        typer.echo(f"alias: {result.alias}")


@app.command()
def download(
    hash_or_alias: str = typer.Argument(...),
    download_path: Path = typer.Argument(..., file_okay=True, dir_okay=False, writable=True),
    password: str | None = typer.Option(None, "-p", "--password", help="Password for encrypted files."),
) -> None:
    """Download a file by hash or alias."""
    service = TobiCloudService(HttpStorage())
    progress = SegmentProgressBar("Downloading")

    try:
        file_hash = service.resolve_file_hash(hash_or_alias)
        _header_key, header = service._resolve_existing_header(file_hash)
        if header.encrypted and password is None:
            password = typer.prompt("Password", hide_input=True)
        result = service.download(file_hash, download_path, password=password, progress=progress)
    except Exception as exc:
        raise typer.Exit(_error(str(exc))) from exc
    finally:
        progress.close()

    typer.echo(f"Downloaded {result.file_hash} to {result.path}")


class SegmentProgressBar:
    def __init__(self, label: str) -> None:
        self.label = label
        self.current = 0
        self._context: Any | None = None
        self._bar: Any | None = None

    def __call__(self, current: int, total: int) -> None:
        if total <= 0:
            return

        if self._bar is None:
            self._context = typer.progressbar(length=total, label=self.label)
            self._bar = self._context.__enter__()

        delta = current - self.current
        if delta > 0:
            self._bar.update(delta)
            self.current = current

    def close(self) -> None:
        if self._context is not None:
            self._context.__exit__(None, None, None)
            self._context = None
            self._bar = None


def _error(message: str) -> int:
    typer.echo(f"Error: {message}", err=True)
    return 1


if __name__ == "__main__":
    app()
