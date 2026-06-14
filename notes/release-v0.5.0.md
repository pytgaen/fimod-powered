# Release notes — 0.5.0

## dockerfile

- Added `writable_dirs` to create runtime-writable directories owned by the non-root user.
- Hardened non-root runtime setup by ensuring `/tmp` has standard sticky permissions and app workdirs are owned by the runtime user.
- Documented generated Python runtime defaults and clarified that `system_packages` is for APT-based images.

## semver_bumper

- Added a mold that calculates the next semantic version from commits since the latest stable tag.
- Supports both `v0.5.0` and `0.5.0` tag styles and can output the next version, tag, bump type, or full JSON details.
- Added fixture coverage and a Git e2e test that exercises real commits, stable tag discovery, prerelease tag exclusion, and `BREAKING CHANGE` footers.
