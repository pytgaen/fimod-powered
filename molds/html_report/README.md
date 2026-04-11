# html_report

Generate a standalone HTML report from any JSON or CSV data. Zero dependencies — a single `.html` file you can open in any browser, share by email, or embed in CI artifacts.

## Why This Mold?

There is no CLI tool that turns JSON or CSV into a standalone, interactive HTML report in one command. Existing alternatives all require more setup:

- **Datasette** — full web server, not a single file
- **Pandas `.to_html()`** — Python code required, no sort/search/theme
- **`json2html`** — Python library, not a CLI
- **Jupyter** — notebook environment, not a one-liner

This mold produces a single `.html` file with no external dependencies — open it in any browser, attach it to an email, or upload it as a CI artifact.

## Features

- **Auto-layout**: arrays of objects → sortable table, single objects → key-value card, lists → item list
- **Search & sort**: built-in client-side filtering and column sorting (no JS framework)
- **Dark mode**: `--arg theme=dark`
- **XSS-safe**: all data is HTML-escaped (`auto_escape=True`)
- **Responsive**: works on desktop and mobile
- **Smart formatting**: numbers right-aligned, nulls styled, nested objects shown as JSON

## Args

| Arg            | Default   | Description                                                                 |
| -------------- | --------- | --------------------------------------------------------------------------- |
| `title`        | `Report`  | Page title and heading                                                      |
| `description`  | *(empty)* | Subtitle shown below the title                                              |
| `theme`        | `light`   | `light` or `dark` (warns and falls back to `light` if unknown)              |
| `timestamp`    | *(empty)* | Generation timestamp shown in footer (e.g. `--arg timestamp="$(date +%F)"`) |
| `null-display` | `null`    | Display for null/missing values: `null`, `empty`, `dash`, or custom text    |

## Examples

### JSON array → sortable table

```bash
echo '[
  {"name": "Alice", "role": "Backend", "score": 92},
  {"name": "Bob", "role": "Frontend", "score": 87},
  {"name": "Charlie", "role": "DevOps", "score": 95}
]' | fimod s -m @html_report --arg title="Team Scores" -o team.html
```

Produces a table with search box, clickable column headers for sorting, and row count.

### CSV → table

```bash
fimod s -i sales.csv -m @html_report --arg title="Sales Q1" -o sales.html
```

### JSON object → key-value card

```bash
echo '{"project": "fimod", "version": "0.2.0", "license": "Apache-2.0"}' \
  | fimod s -m @html_report --arg title="Project Info" -o info.html
```

### API → report (with transform)

```bash
fimod s -i https://jsonplaceholder.typicode.com/users \
  -e '[{"name": u["name"], "email": u["email"], "city": dp_get(u, "address.city")} for u in data]' \
  -m @html_report --arg title="User Directory" \
  -o users.html
```

### Dark mode + description

```bash
fimod s -i results.json -m @html_report \
  --arg title="Audit Report" \
  --arg description="Generated from prod database snapshot" \
  --arg theme=dark \
  -o audit.html
```

### CI artifact (GitHub Actions)

```yaml
# .github/workflows/report.yml
- name: Generate test report
  run: |
    fimod s -i test-results.json -m @html_report \
      --arg title="Test Results" -o report.html
- uses: actions/upload-artifact@v4
  with:
    name: test-report
    path: report.html
```

### Pipe from another command

```bash
kubectl get pods -o json \
  | fimod s -e '[{"name": p["metadata"]["name"], "status": p["status"]["phase"]} for p in data["items"]]' \
  -m @html_report --arg title="Pod Status" -o pods.html
```
