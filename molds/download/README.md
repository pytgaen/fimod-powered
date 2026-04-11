# download

Download a file from a URL and save it to disk (wget-like).

## Usage

```bash
fimod s -i https://example.com/file.tar.gz -m @download
```

With a custom output filename:

```bash
fimod s -i https://example.com/file.tar.gz -m @download --arg out=myfile.tar.gz
```

## Args

| Arg | Required | Description |
|-----|----------|-------------|
| `out` | No | Output filename — defaults to the last path segment of the URL |

## Example

```bash
fimod s -i https://github.com/cli/cli/releases/download/v2.45.0/gh_2.45.0_linux_amd64.tar.gz \
  -m @download --arg out=gh.tar.gz
# → writes gh.tar.gz in the current directory
```

## Chaining with @gh_latest

The natural companion to `@download` is `@gh_latest` — resolve the latest release URL, then download it in one pipeline:

```bash
# Get the latest release URL and download it
fimod s -i https://github.com/sinelaw/fresh/releases/latest \
  -m @gh_latest \
  --arg repo="sinelaw/fresh" \
  --arg asset='fresh-editor_{version}-1_amd64.deb' \
  | fimod s -I - -m @download --arg out=fresh-editor.deb
```

## How it works

The mold uses `input-format=http` to get the raw HTTP response body as bytes, then calls
`set_output_format("raw")` and `set_output_file(filename)` to write the binary content
directly to disk — bypassing JSON serialization entirely.

### Filename resolution order

1. `--arg out=...` if provided
2. `Content-Disposition` header filename (auto-detected from the HTTP response)
3. Last path segment of the URL (stripped of query params)

### Error handling

HTTP responses with status ≥ 400 abort with `gk_fail` instead of writing an error page to disk.

## Mold directives

- `input-format=http` — expose the raw HTTP response (status, headers, body bytes)
