"""
Migrate a Poetry pyproject.toml to Poetry 2 or uv format.

Usage:
  fimod s -i pyproject.toml -m @poetry_migrate -o new_pyproject.toml
  fimod s -i pyproject.toml -m @poetry_migrate -o new_pyproject.toml --arg target=uv
  fimod s -i pyproject.toml -m @poetry_migrate -o new_pyproject.toml --arg target=uv --arg build=setuptools
"""
# fimod: output-format=toml
# fimod: arg=target  "Migration target: poetry2 or uv (default: poetry2)"
# fimod: arg=build   "Build backend for uv target: hatchling, setuptools, flit, pdm, uv (default: hatchling)"
# fimod: arg=index_strategy "uv index-strategy: first-index (default), unsafe-best-match, unsafe-first-match"


def parse_people(items):
    """Parse ["Name <email>"] into [{"name": "Name", "email": "email"}]"""
    people = []
    for item in items:
        if "<" in item and item.endswith(">"):
            parts = item.split("<")
            name = parts[0].strip()
            email = parts[1].strip(">")
            people.append({"name": name, "email": email})
        else:
            people.append({"name": item})
    return people


def convert_constraint(constraint):
    """Convert Poetry constraint to PEP 440."""
    if isinstance(constraint, list):
        # Poetry lists are OR logic, but PEP 440 comma is AND.
        # We join with comma (AND) and warn — no clean PEP 440 OR equivalent.
        converted = [convert_constraint(c) for c in constraint]
        msg_warn(
            "OR constraint " + str(constraint) + " converted to AND ("
            + ",".join(converted) + ") — review manually"
        )
        return ",".join(converted)

    s = str(constraint).strip()

    if s == "*":
        return ">=0.0.0"

    if s.startswith("^"):
        ver = s[1:]
        parts = ver.split(".")
        try:
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            lower = f"{major}.{minor}.{patch}"
            if major > 0:
                upper = f"{major + 1}.0.0"
            elif minor > 0:
                upper = f"0.{minor + 1}.0"
            else:
                upper = f"0.0.{patch + 1}"
            return f">={lower},<{upper}"
        except Exception:
            msg_warn("Could not parse caret constraint: " + s + " — keeping as-is")
            return s

    if s.startswith("~"):
        ver = s[1:]
        parts = ver.split(".")
        try:
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            lower = f"{major}.{minor}.{patch}"
            if len(parts) >= 2:
                upper = f"{major}.{minor + 1}.0"
            else:
                upper = f"{major + 1}.0.0"
            return f">={lower},<{upper}"
        except Exception:
            msg_warn("Could not parse tilde constraint: " + s + " — keeping as-is")
            return s

    # Bare version without operator → pin with ==
    if s and s[0].isdigit():
        return f"=={s}"

    return s


def simplify_python_constraint(s):
    """Trim trailing .0 in version tuples: >=3.9.0,<4.0.0 -> >=3.9,<4.0."""
    return re_sub(r"(\d+\.\d+)\.0(?=\D|$)", r"\1", s)


def _split_operator(s):
    """Split a constraint like '>=3.8' into ('>=', '3.8'). Bare version → '==' op."""
    for op in (">=", "<=", "==", "!=", "~=", ">", "<"):
        if s.startswith(op):
            return op, s[len(op):].strip()
    if s and s[0].isdigit():
        return "==", s
    return None, s


def python_constraint_to_marker(constraint):
    """Convert a Poetry python constraint to PEP 508 marker form."""
    pep = simplify_python_constraint(convert_constraint(constraint))
    parts = [p.strip() for p in pep.split(",") if p.strip()]
    out = []
    for p in parts:
        op, ver = _split_operator(p)
        if op and ver:
            out.append("python_version " + op + " '" + ver + "'")
    return " and ".join(out)


def build_markers(req):
    """Build PEP 508 marker expression from a Poetry dep dict."""
    parts = []
    if "python" in req:
        m = python_constraint_to_marker(req["python"])
        if m:
            parts.append(m)
    if "platform" in req:
        parts.append("sys_platform == '" + str(req["platform"]) + "'")
    if "markers" in req:
        parts.append("(" + str(req["markers"]) + ")")
    return " and ".join(parts)


def _with_markers(base, markers):
    return base + "; " + markers if markers else base


def convert_dependency(name, req, target, path_sources):
    """
    Convert a dependency definition to PEP 508 string, or a list of strings
    for multi-constraint deps.
    path_sources is a dict that gets populated with path dependency sources for uv.
    """
    if isinstance(req, str):
        version = convert_constraint(req)
        return f"{name}{version}" if version and version != "*" else name

    # Multi-constraint: list of dicts (Poetry allows per-env constraints)
    if isinstance(req, list):
        results = []
        for sub in req:
            entry = convert_dependency(name, sub, target, path_sources)
            if entry is None:
                continue
            if isinstance(entry, list):
                results.extend(entry)
            else:
                results.append(entry)
        return results

    if isinstance(req, dict):
        if req.get("allow-prereleases") or req.get("allow_prereleases"):
            msg_warn(
                "'" + name + "': allow-prereleases dropped — no clean PEP 621 "
                "equivalent. Consider [tool.uv] prerelease='allow' globally."
            )

        markers = build_markers(req)

        # Handle path dependencies
        if "path" in req:
            dep_path = req["path"]
            if target == "uv":
                source_entry = {"path": dep_path}
                if req.get("develop", False):
                    source_entry["editable"] = True
                path_sources[name] = source_entry
            return _with_markers(name, markers)

        # Handle URL dependencies
        if "url" in req:
            url = req["url"]
            if target == "uv":
                path_sources[name] = {"url": url}
                return _with_markers(name, markers)
            return _with_markers(f"{name} @ {url}", markers)

        # Handle git dependencies
        if "git" in req:
            git = req["git"]
            if target == "uv":
                source_entry = {"git": git}
                for ref_key in ["branch", "tag", "rev", "subdirectory"]:
                    if ref_key in req:
                        source_entry[ref_key] = req[ref_key]
                if req.get("develop"):
                    source_entry["editable"] = True
                path_sources[name] = source_entry
                return _with_markers(name, markers)
            # For poetry2, use PEP 508 inline
            ref = req.get("branch") or req.get("tag") or req.get("rev")
            suffix = f"@{ref}" if ref else ""
            subdir = req.get("subdirectory")
            subdir_suffix = f"#subdirectory={subdir}" if subdir else ""
            return _with_markers(
                f"{name} @ git+{git}{suffix}{subdir_suffix}", markers
            )

        # Handle version in dict
        if "version" in req:
            # Per-dep source → [tool.uv.sources] { index = "name" } for uv
            if target == "uv" and "source" in req:
                path_sources[name] = {"index": req["source"]}
            version = convert_constraint(req["version"])
            extras = req.get("extras", [])
            if extras:
                extras_str = ",".join(extras)
                base = f"{name}[{extras_str}]{version}"
            else:
                base = f"{name}{version}"
            return _with_markers(base, markers)

        # Dict without version/path/git/url but with markers only → bare name + markers
        if markers:
            return _with_markers(name, markers)

    return None


def convert_deps_list(deps, target, path_sources, dep_strings=None):
    """Convert a Poetry dependency dict to a list of PEP 508 strings."""
    result = []
    for name, constraint in deps.items():
        req = convert_dependency(name, constraint, target, path_sources)
        if not req:
            continue
        if isinstance(req, list):
            result.extend(req)
            if dep_strings is not None and req:
                dep_strings[name] = req[0]
        else:
            result.append(req)
            if dep_strings is not None:
                dep_strings[name] = req
    return result


def normalize_source_priority(source):
    """Normalize Poetry 1.x default/secondary/primary flags to priority string."""
    s = {}
    for k, v in source.items():
        if k not in ("default", "secondary", "primary"):
            s[k] = v
    if source.get("default"):
        s["priority"] = "default"
    elif source.get("primary"):
        s["priority"] = "primary"
    elif source.get("secondary"):
        s["priority"] = "supplemental"
    elif "priority" in source:
        s["priority"] = source["priority"]
    return s


def transform(data, args, **_):
    """Convert Poetry pyproject.toml to PEP 621 / uv / Poetry 2.0 format."""
    target = args.get("target", "poetry2")
    if target == "poetry":
        target = "poetry2"

    tool = data.get("tool", {})
    poetry = tool.get("poetry", {})

    if not poetry:
        return data

    project = {}
    path_sources = {}  # collects path/git deps for [tool.uv.sources]
    dep_strings = {}   # name -> PEP 508 string, used to expand extras

    if "packages" in poetry:
        msg_warn("'packages' config is not migrated — configure your build backend manually")

    # 1. Metadata
    for key in ["name", "version", "description", "readme", "license"]:
        if key in poetry:
            project[key] = poetry[key]

    if "authors" in poetry:
        project["authors"] = parse_people(poetry["authors"])
    if "maintainers" in poetry:
        project["maintainers"] = parse_people(poetry["maintainers"])

    for key in ["keywords", "classifiers", "urls"]:
        if key in poetry:
            project[key] = poetry[key]

    # 2. Dependencies
    if "dependencies" in poetry:
        deps = poetry["dependencies"]
        project["dependencies"] = []

        if "python" in deps:
            project["requires-python"] = simplify_python_constraint(
                convert_constraint(deps.pop("python"))
            )

        project["dependencies"] = convert_deps_list(
            deps, target, path_sources, dep_strings
        )

    # 3. Scripts
    if "scripts" in poetry:
        project["scripts"] = poetry["scripts"]

    # 4. Extras → optional-dependencies
    if "extras" in poetry:
        optional_deps = {}
        for extra_name, extra_deps in poetry["extras"].items():
            optional_deps[extra_name] = [
                dep_strings.get(d, d) for d in extra_deps
            ]
        project["optional-dependencies"] = optional_deps

    # 5. Plugins → entry-points
    if "plugins" in poetry:
        project["entry-points"] = poetry["plugins"]

    # 6. Dev Dependencies & Groups → dependency-groups (PEP 735)
    dependency_groups = {}

    if "dev-dependencies" in poetry:
        dev_deps = convert_deps_list(
            poetry["dev-dependencies"], target, path_sources
        )
        if dev_deps:
            dependency_groups["dev"] = dev_deps

    if "group" in poetry:
        for group_name, group_data in poetry["group"].items():
            if "dependencies" not in group_data:
                continue
            # Poetry 1.2+: [tool.poetry.group.main.dependencies] merges with
            # top-level project.dependencies (PEP 621)
            if group_name == "main":
                if "dependencies" not in project:
                    project["dependencies"] = []
                main_deps = convert_deps_list(
                    group_data["dependencies"], target, path_sources, dep_strings
                )
                project["dependencies"].extend(main_deps)
                continue
            group_deps = convert_deps_list(
                group_data["dependencies"], target, path_sources
            )
            if group_name in dependency_groups:
                dependency_groups[group_name].extend(group_deps)
            else:
                dependency_groups[group_name] = group_deps

    # 7. Build System
    build_system = {}
    if target == "uv":
        build = args.get("build", "hatchling")
        backends = {
            "hatchling": ["hatchling", "hatchling.build"],
            "setuptools": ["setuptools>=61.0", "setuptools.build_meta"],
            "flit": ["flit_core>=3.4", "flit_core.buildapi"],
            "pdm": ["pdm-backend", "pdm.backend"],
            "uv": ["uv-build>=0.7", "uv_build"],
        }
        if build in backends:
            build_system["requires"] = [backends[build][0]]
            build_system["build-backend"] = backends[build][1]
        else:
            msg_warn("Unknown build backend '" + build + "', using hatchling")
            build_system["requires"] = ["hatchling"]
            build_system["build-backend"] = "hatchling.build"
    else:
        build_system["requires"] = ["poetry-core>=2.0.0,<3.0.0"]
        build_system["build-backend"] = "poetry.core.masonry.api"

    # 8. Sources / Index
    tool_uv = {}
    tool_poetry_kept = {}  # preserved under [tool.poetry] for poetry2 target

    if "source" in poetry:
        normalized = [normalize_source_priority(s) for s in poetry["source"]]
        if target == "uv":
            indexes = []
            for s in normalized:
                index = {}
                if "name" in s:
                    index["name"] = s["name"]
                if "url" in s:
                    index["url"] = s["url"]
                pri = s.get("priority")
                if pri == "default":
                    index["default"] = True
                elif pri == "explicit":
                    index["explicit"] = True
                # supplemental/primary have no direct uv equivalent;
                # declaration order defines consultation order
                indexes.append(index)
            if indexes:
                tool_uv["index"] = indexes
            strategy = args.get("index_strategy")
            valid_strategies = (
                "first-index",
                "unsafe-best-match",
                "unsafe-first-match",
            )
            if strategy:
                strategy = strategy.lower()
                if strategy in valid_strategies:
                    tool_uv["index-strategy"] = strategy
                else:
                    msg_warn(
                        "Unknown index_strategy '" + strategy
                        + "' — ignored. Valid: " + ", ".join(valid_strategies)
                    )
            elif len(indexes) > 1:
                msg_warn(
                    "Multiple indexes declared — uv defaults to "
                    "index-strategy='first-index' (differs from Poetry). "
                    "To preserve Poetry semantics rerun with "
                    "--arg index_strategy=unsafe-best-match, or mark private "
                    "indexes with explicit=true and pin deps via "
                    "[tool.uv.sources]."
                )
        else:
            tool_poetry_kept["source"] = normalized

    # Preserve Poetry 2-valid keys that have no PEP 621 equivalent
    for key in ("include", "exclude", "package-mode"):
        if key in poetry and target != "uv":
            tool_poetry_kept[key] = poetry[key]

    if target == "uv" and poetry.get("package-mode") is False:
        msg_warn(
            "package-mode=false dropped — for a uv application project, "
            "remove [build-system] manually or set [tool.uv] package=false "
            "(uv 0.5+)."
        )

    # Path/git sources for uv
    if path_sources and target == "uv":
        tool_uv["sources"] = path_sources

    # 9. Construct Output
    output = {}
    output["project"] = project
    output["build-system"] = build_system

    if dependency_groups:
        output["dependency-groups"] = dependency_groups

    new_tool = tool.copy()
    if "poetry" in new_tool:
        new_tool.pop("poetry")

    if tool_poetry_kept:
        new_tool["poetry"] = tool_poetry_kept

    if tool_uv:
        if "uv" not in new_tool:
            new_tool["uv"] = {}
        uv_section = new_tool["uv"]
        for k, v in tool_uv.items():
            uv_section[k] = v

    if new_tool:
        output["tool"] = new_tool

    return output
