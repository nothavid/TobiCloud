# TobiCloud

TobiCloud is a small Python cloud-storage CLI. It can upload a local file to the
lecture key-value API and download it later by file hash or alias.

The CLI supports optional password-based encryption:

```text
tobicloud upload <path> [-a ALIAS] [-p PASSWORD]
tobicloud download <hash-or-alias> <downloadpath> [-p PASSWORD]
```

## Requirements

- Python 3.12 or newer
- `uv`

Install `uv` from <https://docs.astral.sh/uv/> if it is not already available.

## Setup

From the project root, install the project dependencies:

```bash
uv sync --dev
```

This creates a local `.venv` and installs the `tobicloud` console script into it.

## Windows

For Command Prompt, use the root-level launcher:

```cmd
tobicloud --help
```

The launcher is [tobicloud.cmd](tobicloud.cmd). It uses `.venv\Scripts\tobicloud.exe`
when available and falls back to `uv run tobicloud`.

From PowerShell, run:

```powershell
.\tobicloud.cmd --help
```

## Linux

Use the root-level POSIX launcher:

```bash
./tobicloud --help
```

If needed, mark it executable once:

```bash
chmod +x tobicloud
```

The launcher uses `.venv/bin/tobicloud` when available and falls back to
`uv run tobicloud`.

## macOS

Use the same POSIX launcher as Linux:

```bash
./tobicloud --help
```

If needed, mark it executable once:

```bash
chmod +x tobicloud
```

## Usage

Upload a file without encryption:

```bash
./tobicloud upload spec.md
```

Upload a file with an alias:

```bash
./tobicloud upload spec.md -a test
```

Upload a file with encryption:

```bash
./tobicloud upload spec.md -a test -p password123
```

Download by alias:

```bash
./tobicloud download test downloaded-spec.md -p password123
```

Download by hash:

```bash
./tobicloud download <file-hash> downloaded-file.bin
```

On Windows Command Prompt, use `tobicloud` instead of `./tobicloud`:

```cmd
tobicloud upload spec.md -a test -p password123
tobicloud download test downloaded-spec.md -p password123
```

If a downloaded file is encrypted and `-p` is omitted, the CLI prompts for the
password using hidden input.

## Development

Run the test suite:

```bash
uv run pytest -q
```

Run the installed CLI through `uv`:

```bash
uv run tobicloud --help
```
