"""
Calculate the next semantic version from commits since the last tag.

Usage:
  fimod s -i commits.json -m @semver_bumper --arg current=v0.5.0
  git log --format='%H%x1f%s%x1f%b%x1e' v0.5.0..HEAD \
    | fimod s --input-format txt -m @semver_bumper --arg current=v0.5.0
"""
# fimod: output-format=json
# fimod: arg=current Current version or tag such as v0.5.0 or 0.5.0
# fimod: arg=output Output mode: json/version/tag/bump (default: json)
# fimod: arg=tag-prefix Tag prefix for next_tag: auto/v/none (default: auto)
# fimod: arg=on-none Behavior when no version-worthy commit is found: keep or fail (default: keep)

BUMP_LEVELS = {"none": 0, "patch": 1, "minor": 2, "major": 3}

TYPE_BUMPS = {
    "feat": "minor",
    "fix": "patch",
    "perf": "patch",
    "docs": "none",
    "refactor": "none",
    "chore": "none",
    "test": "none",
    "style": "none",
    "ci": "none",
    "build": "none",
}


def _parse_version(raw):
    value = str(raw or "").strip()
    gk_assert(value, "current version is required (use --arg current=v0.5.0)")

    prefix = ""
    version = value
    if value.startswith("v"):
        prefix = "v"
        version = value[1:]

    parts = version.split(".")
    gk_assert(len(parts) == 3, "current must be a stable SemVer version like v0.5.0 or 0.5.0")

    numbers = []
    for part in parts:
        gk_assert(part.isdigit(), "current must not include prerelease/build metadata")
        numbers.append(int(part))

    return {
        "raw": value,
        "prefix": prefix,
        "version": version,
        "major": numbers[0],
        "minor": numbers[1],
        "patch": numbers[2],
    }


def _tag_prefix(args, inferred_prefix):
    value = args.get("tag-prefix", "auto")
    if value == "auto":
        return inferred_prefix
    if value == "v":
        return "v"
    if value == "none":
        return ""
    gk_fail("tag-prefix must be one of: auto, v, none")
    return inferred_prefix


def _commit_from_message(message):
    lines = str(message or "").splitlines()
    subject = ""
    body_lines = []
    for index, line in enumerate(lines):
        if line.strip():
            subject = line.strip()
            body_lines = lines[index + 1:]
            break
    return {"subject": subject, "body": "\n".join(body_lines), "message": str(message or "")}


def _parse_text_commits(text):
    value = str(text or "")
    commits = []

    if "\x1e" in value:
        for record in value.split("\x1e"):
            if not record.strip():
                continue
            fields = record.strip("\n").split("\x1f")
            if len(fields) >= 3:
                commits.append({
                    "hash": fields[0].strip(),
                    "subject": fields[1].strip(),
                    "body": "\x1f".join(fields[2:]).strip(),
                })
            elif len(fields) == 2:
                commits.append({"hash": fields[0].strip(), "subject": fields[1].strip(), "body": ""})
            else:
                commits.append(_commit_from_message(record))
        return commits

    for line in value.splitlines():
        if line.strip():
            commits.append({"subject": line.strip(), "body": ""})
    return commits


def _extract_current_and_commits(data, args):
    current = args.get("current", "")

    if isinstance(data, dict):
        current = current or data.get("current", "")
        commits = data.get("commits", data.get("items", []))
    elif isinstance(data, list):
        commits = data
    elif isinstance(data, str):
        commits = _parse_text_commits(data)
    else:
        gk_fail("input must be a commit list, an object with commits, or text git log output")
        commits = []

    gk_assert(isinstance(commits, list), "commits must be a list")
    return current, commits


def _normalize_commit(item):
    if isinstance(item, str):
        return _commit_from_message(item)

    gk_assert(isinstance(item, dict), "each commit must be an object or string")

    message = item.get("message", "")
    subject = item.get("subject", "") or item.get("title", "") or item.get("msg", "")
    body = item.get("body", "") or item.get("description", "")

    if message and not subject:
        parsed = _commit_from_message(message)
        subject = parsed["subject"]
        body = body or parsed["body"]

    return {
        "hash": item.get("hash", item.get("sha", item.get("commit", ""))),
        "subject": str(subject or "").strip(),
        "body": str(body or ""),
        "message": str(message or ""),
    }


def _commit_type(subject):
    if ":" not in subject:
        return "", False

    header = subject.split(":", 1)[0].strip()
    breaking = header.endswith("!")
    if breaking:
        header = header[:-1]

    commit_type = header.split("(", 1)[0].strip().lower()
    return commit_type, breaking


def _has_breaking_footer(commit):
    text = "\n".join([
        commit.get("subject", ""),
        commit.get("body", ""),
        commit.get("message", ""),
    ])
    return "BREAKING CHANGE:" in text or "BREAKING-CHANGE:" in text


def _breaking_bump(version):
    if version["major"] == 0:
        return "minor"
    return "major"


def _analyze_commit(commit, version):
    subject = commit.get("subject", "")
    commit_type, breaking_marker = _commit_type(subject)
    breaking = breaking_marker or _has_breaking_footer(commit)

    if breaking:
        return _breaking_bump(version), subject or "BREAKING CHANGE"

    return TYPE_BUMPS.get(commit_type, "none"), subject


def _next_version(version, bump):
    major = version["major"]
    minor = version["minor"]
    patch = version["patch"]

    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    return version["version"]


def transform(data, args, **_):
    current_raw, commit_items = _extract_current_and_commits(data, args)
    version = _parse_version(current_raw)

    counts = {"major": 0, "minor": 0, "patch": 0, "none": 0}
    reasons = []
    best_bump = "none"

    for item in commit_items:
        commit = _normalize_commit(item)
        bump, reason = _analyze_commit(commit, version)
        counts[bump] = counts.get(bump, 0) + 1

        if BUMP_LEVELS[bump] > BUMP_LEVELS[best_bump]:
            best_bump = bump

        if bump != "none":
            reasons.append(reason)

    on_none = args.get("on-none", "keep")
    if best_bump == "none" and on_none == "fail":
        gk_fail("no version-worthy commit found")
    elif on_none not in ("keep", "fail"):
        gk_fail("on-none must be one of: keep, fail")

    next_version = _next_version(version, best_bump)
    tag_prefix = _tag_prefix(args, version["prefix"])

    result = {
        "current": version["version"],
        "current_tag": version["prefix"] + version["version"],
        "next": next_version,
        "next_tag": tag_prefix + next_version,
        "bump": best_bump,
        "reasons": reasons,
        "counts": counts,
        "commit_count": len(commit_items),
    }

    output = args.get("output", "json")
    if output == "json":
        return result
    if output == "version":
        set_output_format("txt")
        return result["next"]
    if output == "tag":
        set_output_format("txt")
        return result["next_tag"]
    if output == "bump":
        set_output_format("txt")
        return result["bump"]

    gk_fail("output must be one of: json, version, tag, bump")
    return result
