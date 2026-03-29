"""
Migrate a Poetry pyproject.toml to Poetry 2 or uv format.

Usage:
  fimod s -i pyproject.toml -m @poetry_migrate -o new_pyproject.toml
  fimod s -i pyproject.toml -m @poetry_migrate -o new_pyproject.toml --arg target=uv
  fimod s -i pyproject.toml -m @poetry_migrate -o new_pyproject.toml --arg target=uv --arg build=setuptools
"""
# fimod: output-format=toml
# fimod: arg=target  Migration target: poetry2 or uv (default: poetry2)
# fimod: arg=build   Build backend for uv target: hatchling, setuptools, flit, pdm, uv (default: hatchling)


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
            return s

    return s


def convert_dependency(name, req, target, path_sources):
    """
    Convert a dependency definition to PEP 508 string.
    path_sources is a dict that gets populated with path dependency sources for uv.
    """
    if isinstance(req, str):
        version = convert_constraint(req)
        return f"{name}{version}" if version and version != "*" else name

    if isinstance(req, dict):
        # Handle path dependencies
        if "path" in req:
            dep_path = req["path"]
            if target == "uv":
                source_entry = {"path": dep_path}
                if req.get("develop", False):
                    source_entry["editable"] = dep_path
                path_sources[name] = source_entry
            return name

        # Handle git dependencies
        if "git" in req:
            git = req["git"]
            if target == "uv":
                source_entry = {"git": git}
                for ref_key in ["branch", "tag", "rev"]:
                    if ref_key in req:
                        source_entry[ref_key] = req[ref_key]
                path_sources[name] = source_entry
                return name
            # For poetry2, use PEP 508 inline
            ref = req.get("branch") or req.get("tag") or req.get("rev")
            suffix = f"@{ref}" if ref else ""
            return f"{name} @ git+{git}{suffix}"

        # Handle version in dict
        if "version" in req:
            version = convert_constraint(req["version"])
            extras = req.get("extras", [])
            if extras:
                extras_str = ",".join(extras)
                return f"{name}[{extras_str}]{version}"
            return f"{name}{version}"

    return None


def convert_deps_list(deps, target, path_sources):
    """Convert a Poetry dependency dict to a list of PEP 508 strings."""
    result = []
    for name, constraint in deps.items():
        req = convert_dependency(name, constraint, target, path_sources)
        if req:
            result.append(req)
    return result


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
            project["requires-python"] = convert_constraint(deps.pop("python"))

        project["dependencies"] = convert_deps_list(deps, target, path_sources)

    # 3. Scripts
    if "scripts" in poetry:
        project["scripts"] = poetry["scripts"]

    # 4. Extras → optional-dependencies
    if "extras" in poetry:
        optional_deps = {}
        for extra_name, extra_deps in poetry["extras"].items():
            optional_deps[extra_name] = extra_deps
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
            if "dependencies" in group_data:
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
    if "source" in poetry and target == "uv":
        indexes = []
        for source in poetry["source"]:
            index = {}
            if "name" in source:
                index["name"] = source["name"]
            if "url" in source:
                index["url"] = source["url"]
            if "default" in source and source["default"]:
                index["default"] = True
            indexes.append(index)
        if indexes:
            tool_uv["index"] = indexes

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

    if tool_uv:
        if "uv" not in new_tool:
            new_tool["uv"] = {}
        uv_section = new_tool["uv"]
        for k, v in tool_uv.items():
            uv_section[k] = v

    if new_tool:
        output["tool"] = new_tool

    return output
