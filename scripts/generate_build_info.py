#!/usr/bin/env python3
"""Generate deployment metadata for the browser-facing build indicator."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "build-info.js"
VERSION = "0.1.0"
TIME_ZONE = "Europe/Athens"

COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
SHORT_SHA_RE = re.compile(r"^[0-9a-f]{7}$")
BUILD_STAMP_RE = re.compile(r"^[0-9]{8}_[0-9]{4}$")
BUILD_INFO_RE = re.compile(
    r"\Awindow\.NTT_BUILD_INFO = Object\.freeze\(\{\n"
    r"  version: '([^']+)',\n"
    r"  buildStamp: '([^']+)',\n"
    r"  shortSha: '([^']+)'\n"
    r"\}\);\n?\Z"
)


def _short_sha(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not COMMIT_SHA_RE.fullmatch(candidate):
        return None
    return candidate[:7].lower()


def resolve_commit_sha() -> str:
    """Return the first valid deployment or repository commit SHA."""

    for variable in ("GITHUB_SHA", "CF_PAGES_COMMIT_SHA"):
        candidate = _short_sha(os.environ.get(variable))
        if candidate is not None:
            return candidate

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None

    if result is not None and result.returncode == 0:
        candidate = _short_sha(result.stdout)
        if candidate is not None:
            return candidate

    return "dev"


def _athens_time_zone() -> ZoneInfo:
    """Load Europe/Athens, including Git for Windows system tzdata fallback."""

    try:
        return ZoneInfo(TIME_ZONE)
    except ZoneInfoNotFoundError as original_error:
        git_executable = shutil.which("git")
        candidates: list[Path] = []
        if git_executable:
            git_root = Path(git_executable).resolve().parent.parent
            candidates.extend(
                (
                    git_root / "mingw64" / "share" / "zoneinfo" / TIME_ZONE,
                    git_root / "usr" / "share" / "zoneinfo" / TIME_ZONE,
                )
            )

        for candidate in candidates:
            try:
                with candidate.open("rb") as zone_file:
                    return ZoneInfo.from_file(zone_file, key=TIME_ZONE)
            except (OSError, ValueError):
                continue

        raise RuntimeError(
            f"IANA time-zone data for {TIME_ZONE} is unavailable"
        ) from original_error


def render_build_info(build_stamp: str, short_sha: str) -> str:
    """Return the JavaScript build metadata file."""

    return (
        "window.NTT_BUILD_INFO = Object.freeze({\n"
        f"  version: '{VERSION}',\n"
        f"  buildStamp: '{build_stamp}',\n"
        f"  shortSha: '{short_sha}'\n"
        "});\n"
    )


def validate_build_info(content: str) -> str:
    """Validate either the committed fallback or generated deployment data."""

    match = BUILD_INFO_RE.fullmatch(content)
    if match is None:
        raise ValueError("file does not match the expected JavaScript structure")

    version, build_stamp, short_sha = match.groups()
    if version != VERSION:
        raise ValueError(f"version must be {VERSION!r}")

    if build_stamp == "local" and short_sha == "dev":
        return f"v {version}_{build_stamp}_{short_sha}"
    if build_stamp == "local" or short_sha == "dev":
        raise ValueError("local fallback requires buildStamp 'local' and shortSha 'dev'")

    if not BUILD_STAMP_RE.fullmatch(build_stamp):
        raise ValueError("buildStamp must use YYYYMMDD_HHMM")
    try:
        datetime.strptime(build_stamp, "%Y%m%d_%H%M")
    except ValueError as exc:
        raise ValueError("buildStamp is not a valid date and time") from exc
    if not SHORT_SHA_RE.fullmatch(short_sha):
        raise ValueError("shortSha must contain exactly 7 lowercase hexadecimal characters")

    return f"v {version}_{build_stamp}_{short_sha}"


def _check_existing() -> int:
    try:
        content = OUTPUT.read_text(encoding="utf-8")
        label = validate_build_info(content)
    except FileNotFoundError:
        print(f"{OUTPUT.relative_to(ROOT)} is missing.", file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(
            f"Invalid {OUTPUT.relative_to(ROOT)}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"Build information check passed: {label}.")
    return 0


def _generate() -> int:
    try:
        timestamp = datetime.now(_athens_time_zone()).strftime("%Y%m%d_%H%M")
        short_sha = resolve_commit_sha()
        content = render_build_info(timestamp, short_sha)
        with OUTPUT.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(content)
    except (OSError, RuntimeError) as exc:
        print(f"Build information generation failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Generated {OUTPUT.relative_to(ROOT)}: "
        f"v {VERSION}_{timestamp}_{short_sha}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the committed fallback or generated deployment metadata",
    )
    args = parser.parse_args(argv)
    return _check_existing() if args.check else _generate()


if __name__ == "__main__":
    raise SystemExit(main())
