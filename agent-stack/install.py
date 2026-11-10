#!/usr/bin/env python3
"""Install pinned skill sources into a project without replacing existing files."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} TARGET_PROJECT")
    target = Path(sys.argv[1]).resolve()
    if not target.is_dir():
        raise SystemExit(f"Target directory does not exist: {target}")

    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "sources.json").read_text())
    vendor = target / ".agent-stack" / "vendor"
    skills_dir = target / ".agents" / "skills"
    vendor.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    clones = []
    for source in manifest["sources"]:
        checkout = vendor / source["name"]
        if checkout.exists():
            current = subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
            ).strip()
            if current != source["revision"]:
                raise SystemExit(f"{checkout} exists at {current}; expected {source['revision']}")
        else:
            clones.append((source, checkout))

    for source, checkout in clones:
        checkout.mkdir(parents=True)
        try:
            run("git", "init", str(checkout))
            run("git", "-C", str(checkout), "remote", "add", "origin", source["url"])
            run("git", "-C", str(checkout), "fetch", "--depth", "1", "origin", source["revision"])
            run("git", "-C", str(checkout), "checkout", "--detach", "FETCH_HEAD")
        except Exception:
            shutil.rmtree(checkout, ignore_errors=True)
            raise
        print(f"Fetched {source['name']} @ {source['revision']}")

    links = []
    for source in manifest["sources"]:
        checkout = vendor / source["name"]
        for rel in source["skills"]:
            path = checkout / rel
            candidates = [path] if (path / "SKILL.md").is_file() else sorted(
                child for child in path.iterdir()
                if child.is_dir() and (child / "SKILL.md").is_file()
            )
            for skill in candidates:
                link = skills_dir / (checkout.name if not rel else skill.name)
                if link.exists() or link.is_symlink():
                    if link.is_symlink() and link.resolve() == skill.resolve():
                        continue
                    raise SystemExit(f"Refusing to replace existing skill path: {link}")
                links.append((link, skill))

    for link, skill in links:
        if not skill.is_dir() or not (skill / "SKILL.md").is_file():
            raise SystemExit(f"Skill source missing SKILL.md: {skill}")
        link.symlink_to(os.path.relpath(skill, link.parent), target_is_directory=True)
        print(f"Linked {link.name}")

    print(f"Skills installed in {skills_dir}")


if __name__ == "__main__":
    main()
