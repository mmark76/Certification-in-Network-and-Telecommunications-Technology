#!/usr/bin/env python3
"""Report empty or duplicate HTML id attributes."""

from __future__ import annotations

import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def html_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.html")
        if ".git" not in path.relative_to(ROOT).parts
    )


class IDParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[tuple[str, int]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del tag
        for name, value in attrs:
            if name == "id":
                self.ids.append((value or "", self.getpos()[0]))


def main() -> int:
    errors: list[str] = []
    files = html_files()
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        parser = IDParser()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{relative}: cannot read valid UTF-8 HTML: {exc}")
            continue

        locations: dict[str, list[int]] = defaultdict(list)
        for html_id, line in parser.ids:
            if not html_id:
                errors.append(f"{relative}:{line}: id attribute must not be empty")
                continue
            locations[html_id].append(line)

        for html_id, lines in sorted(locations.items()):
            if len(lines) > 1:
                joined_lines = ", ".join(str(line) for line in lines)
                errors.append(
                    f"{relative}: duplicate id {html_id!r} on lines {joined_lines}"
                )

    if errors:
        print(f"HTML ID check failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"HTML ID check passed for {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
