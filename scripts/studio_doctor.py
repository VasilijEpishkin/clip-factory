#!/usr/bin/env python3
"""Non-destructive Clip Factory environment preflight (stdlib only)."""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def check_command(name):
    path = shutil.which(name)
    return {"status": "ok" if path else "missing", "detail": path or "not in PATH"}

def check_file(path):
    return {"status": "ok" if path.exists() else "missing", "detail": str(path)}

def check_python():
    ok = sys.version_info >= (3, 11)
    return {"status": "ok" if ok else "missing", "detail": sys.version.split()[0]}

def collect():
    checks = {"python>=3.11": check_python()}
    for name in ("ffmpeg", "ffprobe", "uv", "node", "npm", "yt-dlp"):
        checks[name] = check_command(name)
    for name in ("pyproject.toml", "uv.lock", "agent-stack/sources.json",
                 "remotion/package-lock.json", "hyperframes/package-lock.json"):
        checks[name] = check_file(ROOT / name)
    checks["optional:hermes"] = check_command("hermes")
    checks["optional:codex"] = check_command("codex")
    checks["optional:claude"] = check_command("claude")
    checks["optional:blender"] = check_command("blender")
    checks["optional:rclone"] = check_command("rclone")
    checks["optional:python-venv"] = check_file(ROOT / ".venv" / "bin" / "python")
    return checks

def main():
    parser = argparse.ArgumentParser(description="Read-only media studio environment check")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()
    checks = collect()
    required = [name for name in checks if not name.startswith("optional:")]
    ready = all(checks[name]["status"] == "ok" for name in required)
    if args.json:
        print(json.dumps({"ready": ready, "checks": checks}, ensure_ascii=False, indent=2))
    else:
        for name, result in checks.items():
            print(f'{result["status"].upper():7} {name:34} {result["detail"]}')
        print("Required prerequisites present" if ready else "Some required prerequisites are missing")
    return 0 if ready else 1

if __name__ == "__main__":
    raise SystemExit(main())
