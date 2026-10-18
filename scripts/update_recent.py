#!/usr/bin/env python3
"""Refresh the 'Live Repository Feed' block in README.md.

Reads the owner's most recently pushed repositories from the GitHub API and
rewrites everything between the LIVE_FEED markers in README.md. Safe to run
locally and inside GitHub Actions; it fails loudly instead of corrupting the
README if markers are missing.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

USER = "Srisai16"
PROFILE_REPO = "Srisai16"          # excluded from the feed
LIMIT = 6
README = Path("README.md")
START = "<!-- LIVE_FEED:START -->"
END = "<!-- LIVE_FEED:END -->"

headers = {"Accept": "application/vnd.github+json", "User-Agent": "Srisai16-profile-readme"}
if os.getenv("GITHUB_TOKEN"):
    headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]


def get(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def relative(iso):
    if not iso:
        return "—"
    pushed = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (dt.datetime.now(dt.timezone.utc) - pushed).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def collect():
    repos, page = [], 1
    while True:
        batch = get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner&sort=pushed")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    repos = [r for r in repos if r["name"] != PROFILE_REPO]
    repos.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    return repos[:LIMIT]


def render(repos):
    lines = [
        "> Auto-refreshed daily by GitHub Actions from the most recently pushed repositories.",
        "",
        "| Repository | Focus | Stack | Last push |",
        "|---|---|---|---|",
    ]
    for r in repos:
        name = r["name"].replace("|", "\\|")
        desc = (r.get("description") or "—").strip().rstrip(".")
        desc = desc.replace("|", "\\|")
        if len(desc) > 90:
            desc = desc[:87] + "..."
        lang = (r.get("language") or "").replace("|", "\\|")
        if r.get("fork"):
            stack = f"{lang} · fork" if lang else "fork"
        else:
            stack = lang or "—"
        lines.append(f"| [**{name}**]({r['html_url']}) | {desc} | `{stack}` | {relative(r.get('pushed_at'))} |")
    return "\n".join(lines)


def main():
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit(f"FATAL: markers {START} / {END} not found in {README}")
    block = f"{START}\n{render(collect())}\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.DOTALL)
    README.write_text(updated, encoding="utf-8")
    print("Live feed updated.")


if __name__ == "__main__":
    main()
