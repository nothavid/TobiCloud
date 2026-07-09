Here is the complete, consolidated project specification.

**Project Goal**

Build a simple Python cloud storage project named TobiCloud.

The project must provide a Typer-based CLI with two commands:

```bash
tobicloud upload <path>
tobicloud download <hash-or-alias> <downloadpath>
```

The CLI is only the interface. File loading, file storing, encryption, decryption, encoding, and storage communication should live in separate components/modules.

**CLI Requirements**

`upload`:

```bash
tobicloud upload <path> [-p PASSWORD] [-a ALIAS]
```

- `<path>` is the local file path to upload.
- `-p PASSWORD` is optional.
- If `-p` is provided, the file must be encrypted before upload.
- If `-p` is omitted, the file is uploaded without encryption.
- `-a ALIAS` is optional.
- If an alias is provided, store an alias mapping after upload.

`download`:

```bash
tobicloud download <hash-or-alias> <downloadpath> [-p PASSWORD]
```

- `<hash-or-alias>` can be either a file hash or an alias.
- `<downloadpath>` is the exact target file path to write to.
- `-p PASSWORD` is optional.
- If the downloaded file header says the file is encrypted and `-p` was not provided, prompt the user for the password using hidden input.
- If the file is encrypted, use the password to decrypt it.
- If the file is not encrypted, ignore any provided password.

**Raw File Processing**

Implement a separate component that can:

1. Load raw bytes from a file.
2. Optionally encrypt those bytes.
3. Convert the resulting bytes to base64 without padding.
4. Reverse the process:
   - restore padding as needed,
   - base64-decode,
   - optionally decrypt,
   - write the raw bytes back to disk.

Base64 strings must omit `=` padding.

**Encryption Requirements**

Encryption is optional and only used when a password is provided during upload.

Use a PBKDF2-derived AES-256 key.

- PBKDF2 iterations: `200_000`
- Salt: no per-file salt should be used.
- If the library requires a salt, use a fixed salt constant.
- AES key length: 256 bits.
- Use a reasonable/default AES mode.
- The encryption format must include whatever minimal metadata is needed to decrypt, but avoid putting encryption metadata into the storage header.
- The storage header must remain small enough to fit in one storage value.
- The live API rejects `text` values longer than 500 characters, so storage values must be capped at 500 characters.

**Remote Storage API**

The cloud storage behaves like a key-value dictionary, but is accessed through a simple HTTP API.

To retrieve a value for a key:

```text
GET http://webtechlecture.appspot.com/chat/posting/list?userid=<key>
```

The specification originally described the response as a JSON array of objects.

The live API actually returns a JSON wrapper object:

```json
{
  "status": "ok",
  "message": "...",
  "result": []
}
```

The array of stored entries is in the `result` field.

For compatibility, the implementation may accept both the original direct-array shape and the live wrapper-object shape.

Each object has a `text` attribute.

The value for the key is the `text` value of the **last** object in the returned array.

If the array is empty, the key is unused.

To store a value for a key:

```text
GET http://webtechlecture.appspot.com/chat/posting/new?userid=<key>&text=<value>
```

This creates a new entry. Even though this mutates data, the API uses GET.

Since retrieval uses the last entry, storing a new value for an existing key effectively updates it.

**Hashing**

Use SHA-256 hex digests.

After optional encryption and base64-without-padding encoding, compute:

```text
file_hash = sha256(base64_payload)
```

This `file_hash` is the public identifier returned to the user.

However, the header is **not** stored directly under `file_hash`.

Instead, the initial header key is:

```text
header_key = sha256(file_hash)
```

This is intended to prevent someone from deriving segment keys directly from a discovered header key.

**Segment Storage**

The base64 payload must be split into segments of up to 500 base64 characters each.

The original design used 512-character segments, but the live API returns HTTP 500 for `text` values above 500 characters.

For a segment with logical segment number `n`, starting at `0`, the preferred segment key is:

```text
segment_key = sha256(f"{file_hash}-{n}")
```

Before storing a segment, check whether that segment key is already taken.

If the key is unused, store the segment there.

If the key is already taken, skip that logical index, record `n` in the skipped list, and try the next integer index for the same payload segment.

Example:

- Payload segment 0 wants index 0.
- If `sha256(f"{file_hash}-0")` is taken, record `0` in skipped list.
- Try index 1.
- If index 1 is free, store payload segment 0 there.
- Continue with the next payload segment at index 2.

The header field `l` means the actual number of payload segments, excluding skipped indices.

The header field `s` contains all skipped segment numbers.

During download, reconstruct the payload by reading segment indices starting at `0`, skipping any indices listed in `s`, until `l` actual segments have been collected.

**Header Storage**

After all segments are uploaded, create a header object:

```json
{
  "a": "<alias or null>",
  "e": true,
  "l": 123,
  "s": [0, 4, 9]
}
```

Fields:

- `a`: the alias, or `null` if no alias was provided.
- `e`: boolean indicating whether the file is encrypted.
- `l`: integer number of actual payload segments.
- `s`: array of integer skipped segment numbers.

The header value stored remotely is:

```text
base64_without_padding(json_string(header_object))
```

The encoded header must fit in one storage value.

**Header Key Collision Handling**

The initial header key is:

```text
header_key = sha256(file_hash)
```

Before storing the header, check whether the key already exists.

If the key exists and contains a valid header, treat the file as already uploaded.

A valid header means:

- The stored value is a base64-without-padding string.
- It decodes to valid JSON.
- The JSON object contains exactly or at least the required fields:
  - `a`
  - `e`
  - `l`
  - `s`
- `e` is a boolean.
- `l` is an integer.
- `s` is an array of integers.
- `a` is either a string or null.

If the key exists but does not contain a valid header, derive a new candidate key:

```text
header_key = sha256(header_key)
```

Repeat until finding either:

- an existing valid header, meaning the file is already uploaded, or
- an unused key, where the new header should be stored.

Download by file hash must use the same chain:

1. Start with `sha256(file_hash)`.
2. If the key contains an invalid occupied value, rehash the key and try again.
3. Use the first valid header found.
4. If no valid header is found before reaching an unused key, the file does not exist.

**Alias Storage**

If an alias is provided during upload, store an alias mapping.

Alias key:

```text
alias_key = f"a:{sha256(alias)}"
```

Alias value:

```text
file_hash
```

To download by alias:

1. Compute `alias_key = f"a:{sha256(alias)}"`.
2. Retrieve the value stored at that key.
3. Treat that value as the `file_hash`.
4. Resolve the header using the header key chain described above.

If the alias key already exists, storing a new value updates it because retrieval always uses the last entry.

**Download Process**

Given `<hash-or-alias>`:

1. Try resolving it as an alias first:
   - look up `a:{sha256(input)}`.
   - if found, use the retrieved value as `file_hash`.
2. If no alias is found, treat the input directly as `file_hash`.
3. Resolve the header using the header key chain.
4. Decode and validate the header.
5. Read payload segments:
   - iterate segment indices starting from `0`,
   - skip indices in `s`,
   - retrieve segment values using `sha256(f"{file_hash}-{n}")`,
   - collect exactly `l` actual segments.
6. Concatenate the collected segment strings into the full base64 payload.
7. If `e` is true:
   - require a password,
   - use `-p PASSWORD` if provided,
   - otherwise prompt with hidden input.
8. Decode and optionally decrypt the payload.
9. Write the final bytes to `<downloadpath>`.

**Dependencies**

Use:

- `typer` for the CLI.
- `requests` or `httpx` for HTTP communication.
- `cryptography` for AES/PBKDF2 encryption.

It is acceptable to use `uv` to install dependencies.
