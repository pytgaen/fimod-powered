# Skylos to GitLab Code Quality

This mold converts JSON reports from `duriantaco/skylos` (a Python static analysis tool) into the GitLab Code Quality (Code Climate) format. This allows Skylos results to be visualized directly in GitLab Merge Requests.

## Usage

```bash
fimod s -i skylos_report.json -m @skylos_to_gitlab -o code_quality.json

# Filter out low-confidence results (potential false positives)
fimod s -i skylos_report.json -m @skylos_to_gitlab --arg min-confidence=80 -o code_quality.json
```

### Arguments

| Argument | Default | Description |
| :--- | :--- | :--- |
| `min-confidence` | `0` (no filter) | Minimum confidence threshold (0-100). Items below this value are excluded. |

### In a GitLab CI pipeline

```yaml
code_quality:
  script:
    - skylos --json > skylos_report.json
    - fimod s -i skylos_report.json -m @skylos_to_gitlab -o gl-code-quality-report.json
  artifacts:
    reports:
      codequality: gl-code-quality-report.json
```

## Transformation Logic

The converter maps Skylos report sections to Code Climate issue categories:

| Skylos Section | Code Climate `check_name` |
| :--- | :--- |
| `unused_functions` | `unused-function` |
| `unused_imports` | `unused-import` |
| `unused_variables` | `unused-variable` |
| `unused_classes` | `unused-class` |
| `unused_parameters` | `unused-parameter` |
| `unused_files` | `dead-file` |

### Confidence & Severity

Skylos reports a `confidence` score (0-100) for each item. The mold uses it in two ways:

- **Filtering**: Pass `--arg min-confidence=N` to exclude items with confidence below the threshold.
- **Severity mapping**: Items with `confidence = 100` get severity `info`. Items with lower confidence get severity `minor`.

### Fingerprinting
A deterministic fingerprint is generated for each issue using the most qualified name available (`full_name` → `name`), the check name, file path, and line number. This allows GitLab to track issues across commits.

## Output Format

The output is a JSON array of issue objects:

```json
[
  {
    "description": "Unused function: my_func",
    "check_name": "unused-function",
    "fingerprint": "a1b2c3d4",
    "severity": "info",
    "location": {
      "path": "src/main.py",
      "lines": {
        "begin": 42
      }
    }
  }
]
```
