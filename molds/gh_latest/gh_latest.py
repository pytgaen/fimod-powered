"""
Get the latest release tag or download URL from a GitHub repository.

Usage:
  fimod s -i https://github.com/owner/repo/releases/latest -m @gh_latest
  fimod s -i https://github.com/owner/repo/releases/latest -m @gh_latest \
        --arg repo=owner/repo --arg asset=myapp-{version}-linux.tar.gz

When --arg asset is provided, returns the full download URL for that release asset.
Without it, returns the bare tag (e.g. v1.2.3).
"""
# fimod: input-format=http, no-follow, output-format=txt
# fimod: arg=repo  "GitHub repository (owner/repo) - required for download URL"
# fimod: arg=asset  "Asset filename pattern - supports {tag} and {version} placeholders"

def transform(data, args, **_):
    location = data["headers"].get("location", "")
    gk_assert("/releases/" in location, "URL must point to a GitHub releases page (e.g. https://github.com/owner/repo/releases/latest)")
    tag = location.rstrip("/").split("/")[-1]
    version = tag.removeprefix("v")

    repo = args.get("repo", "")
    asset = args.get("asset", "")

    msg_info(f"Latest release tag / version: {tag} / {version}")

    if repo and asset:
        msg_info(f"repo: {repo}, asset: {asset}")

        asset = asset.replace("{tag}", tag).replace("{version}", version)
        return f"https://github.com/{repo}/releases/download/{tag}/{asset}"

    return tag
