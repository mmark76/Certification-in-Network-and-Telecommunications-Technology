#!/usr/bin/env python3
"""Check local href/src targets and HTML fragments."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data", "blob"}


def html_files() -> list[Path]:
    return sorted(
        path.resolve()
        for path in ROOT.rglob("*.html")
        if ".git" not in path.relative_to(ROOT).parts
    )


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str, int]] = []
        self.ids: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        line = self.getpos()[0]
        for name, value in attrs:
            if name == "id" and value:
                self.ids.add(value)
            if name in {"href", "src"} and value is not None:
                self.references.append((name, value.strip(), line))


def _within_root(path: Path) -> bool:
    try:
        path.relative_to(ROOT)
    except ValueError:
        return False
    return True


def _display(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    errors: list[str] = []
    files = html_files()
    parsed: dict[Path, LinkParser] = {}

    for path in files:
        parser = LinkParser()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{_display(path)}: cannot read valid UTF-8 HTML: {exc}")
            continue
        parsed[path] = parser

    for source, parser in list(parsed.items()):
        for attribute, raw_reference, line in parser.references:
            if not raw_reference:
                continue
            parts = urlsplit(raw_reference)
            scheme = parts.scheme.lower()
            if scheme in EXTERNAL_SCHEMES or parts.netloc:
                continue
            if scheme:
                errors.append(
                    f"{_display(source)}:{line}: unsupported {attribute} URL scheme "
                    f"in {raw_reference!r}"
                )
                continue
            if "\\" in parts.path:
                errors.append(
                    f"{_display(source)}:{line}: local URL must use '/' in "
                    f"{raw_reference!r}"
                )
                continue

            decoded_path = unquote(parts.path)
            if decoded_path.startswith("/"):
                candidate = ROOT / decoded_path.lstrip("/")
            elif decoded_path:
                candidate = source.parent / decoded_path
            else:
                candidate = source
            target = candidate.resolve()

            if not _within_root(target):
                errors.append(
                    f"{_display(source)}:{line}: local reference escapes the repository: "
                    f"{raw_reference!r}"
                )
                continue
            if target.is_dir():
                target = (target / "index.html").resolve()
            if not target.is_file():
                errors.append(
                    f"{_display(source)}:{line}: missing local target "
                    f"{raw_reference!r}"
                )
                continue

            fragment = unquote(parts.fragment)
            if not fragment or target.suffix.lower() != ".html":
                continue

            target_parser = parsed.get(target)
            if target_parser is None:
                target_parser = LinkParser()
                try:
                    target_parser.feed(target.read_text(encoding="utf-8"))
                    target_parser.close()
                except (OSError, UnicodeDecodeError) as exc:
                    errors.append(
                        f"{_display(source)}:{line}: cannot inspect fragment target "
                        f"{_display(target)}: {exc}"
                    )
                    continue
                parsed[target] = target_parser
            if fragment not in target_parser.ids:
                errors.append(
                    f"{_display(source)}:{line}: missing HTML fragment "
                    f"{fragment!r} in {_display(target)}"
                )

    if errors:
        print(f"Internal link check failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Internal link check passed for {len(files)} HTML file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
