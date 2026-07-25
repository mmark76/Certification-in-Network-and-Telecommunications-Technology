#!/usr/bin/env python3
"""Parse the repository's deliberately small, block-style YAML subset.

This is not a general YAML implementation. It supports only the constructs
used by data/curriculum.yml:

* mappings with simple ASCII keys,
* block sequences,
* strings, integers, booleans and null,
* quoted strings,
* the empty flow collections [] and {}.

Unsupported YAML features are rejected instead of being interpreted
approximately. In particular, anchors, aliases, tags, merge keys, multiline
scalars and non-empty flow collections are not accepted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


KEY_VALUE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:[ ]*(.*))?$")
INTEGER_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
AMBIGUOUS_NUMBER_RE = re.compile(
    r"^[+-]?(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+|[0-9]+[eE][+-]?[0-9]+)$"
)


class CurriculumYAMLError(ValueError):
    """Raised when curriculum YAML is outside the supported safe subset."""


@dataclass(frozen=True)
class _Line:
    number: int
    indent: int
    text: str


def _error(source: str, line: int, message: str) -> CurriculumYAMLError:
    return CurriculumYAMLError(f"{source}:{line}: {message}")


def _prepare_lines(text: str, source: str) -> list[_Line]:
    prepared: list[_Line] = []
    for number, raw_line in enumerate(text.splitlines(), start=1):
        if number == 1:
            raw_line = raw_line.removeprefix("\ufeff")
        if "\t" in raw_line:
            raise _error(source, number, "tabs are not allowed")

        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            raise _error(source, number, "indentation must use multiples of two spaces")

        content = raw_line[indent:].rstrip()
        if content in {"---", "..."}:
            raise _error(source, number, "YAML document markers are not supported")
        prepared.append(_Line(number=number, indent=indent, text=content))

    return prepared


def _split_key_value(text: str, source: str, line: int) -> tuple[str, str]:
    match = KEY_VALUE_RE.fullmatch(text)
    if not match:
        raise _error(source, line, "expected a simple 'key: value' mapping entry")
    key = match.group(1)
    if key == "<<":
        raise _error(source, line, "YAML merge keys are not supported")
    return key, match.group(2) or ""


def _parse_single_quoted(value: str, source: str, line: int) -> str:
    if len(value) < 2 or not value.endswith("'"):
        raise _error(source, line, "unterminated single-quoted string")

    inner = value[1:-1]
    output: list[str] = []
    index = 0
    while index < len(inner):
        if inner[index] != "'":
            output.append(inner[index])
            index += 1
            continue
        if index + 1 >= len(inner) or inner[index + 1] != "'":
            raise _error(source, line, "single quotes inside a string must be doubled")
        output.append("'")
        index += 2
    return "".join(output)


def _parse_scalar(value: str, source: str, line: int) -> Any:
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "[]":
        return []
    if value == "{}":
        return {}

    lowered = value.lower()
    if lowered in {"null", "true", "false", "~"}:
        raise _error(source, line, "use only lowercase null, true or false")

    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise _error(source, line, f"invalid double-quoted string: {exc.msg}") from exc
        if not isinstance(parsed, str):
            raise _error(source, line, "double-quoted scalars must be strings")
        return parsed

    if value.startswith("'"):
        return _parse_single_quoted(value, source, line)

    if value.startswith(("[", "{")):
        raise _error(source, line, "non-empty flow collections are not supported")
    if value.startswith(("&", "*", "!")):
        raise _error(source, line, "anchors, aliases and tags are not supported")
    if value.startswith(("|", ">")):
        raise _error(source, line, "multiline scalars are not supported")
    if value.startswith(("- ", "? ")):
        raise _error(source, line, "ambiguous plain scalar; quote this value")
    if " #" in value:
        raise _error(source, line, "inline comments are not supported; use a separate line")
    if ": " in value:
        raise _error(source, line, "plain strings containing ': ' must be quoted")

    if INTEGER_RE.fullmatch(value):
        return int(value)
    if AMBIGUOUS_NUMBER_RE.fullmatch(value):
        raise _error(source, line, "floating-point values are not supported")

    return value


class _Parser:
    def __init__(self, lines: list[_Line], source: str) -> None:
        self.lines = lines
        self.source = source

    @staticmethod
    def _is_sequence_line(line: _Line) -> bool:
        return line.text == "-" or line.text.startswith("- ")

    def parse(self) -> Any:
        if not self.lines:
            raise CurriculumYAMLError(f"{self.source}: document is empty")
        if self.lines[0].indent != 0:
            raise _error(self.source, self.lines[0].number, "top-level content must start at column 1")

        value, index = self._parse_block(0, 0)
        if index != len(self.lines):
            line = self.lines[index]
            raise _error(self.source, line.number, "unexpected trailing content")
        return value

    def _parse_block(self, index: int, indent: int) -> tuple[Any, int]:
        if index >= len(self.lines):
            raise CurriculumYAMLError(f"{self.source}: unexpected end of document")
        line = self.lines[index]
        if line.indent != indent:
            raise _error(
                self.source,
                line.number,
                f"expected indentation of {indent} spaces, found {line.indent}",
            )
        if self._is_sequence_line(line):
            return self._parse_sequence(index, indent)
        return self._parse_mapping(index, indent)

    def _assign_mapping_entry(
        self,
        result: dict[str, Any],
        index: int,
        indent: int,
        text_override: str | None = None,
    ) -> int:
        line = self.lines[index]
        text = line.text if text_override is None else text_override
        key, raw_value = _split_key_value(text, self.source, line.number)
        if key in result:
            raise _error(self.source, line.number, f"duplicate mapping key {key!r}")

        next_index = index + 1
        if raw_value:
            result[key] = _parse_scalar(raw_value, self.source, line.number)
            return next_index

        child_indent = indent + 2
        if next_index >= len(self.lines):
            raise _error(self.source, line.number, f"mapping key {key!r} has no value")
        child_line = self.lines[next_index]
        if child_line.indent != child_indent:
            raise _error(
                self.source,
                child_line.number,
                f"value for {key!r} must be indented {child_indent} spaces",
            )
        result[key], next_index = self._parse_block(next_index, child_indent)
        return next_index

    def _parse_mapping(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while index < len(self.lines):
            line = self.lines[index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise _error(self.source, line.number, "unexpected extra indentation")
            if self._is_sequence_line(line):
                raise _error(self.source, line.number, "cannot mix a sequence into this mapping")
            index = self._assign_mapping_entry(result, index, indent)
        return result, index

    def _parse_sequence(self, index: int, indent: int) -> tuple[list[Any], int]:
        result: list[Any] = []
        while index < len(self.lines):
            line = self.lines[index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise _error(self.source, line.number, "unexpected extra indentation")
            if not self._is_sequence_line(line):
                raise _error(self.source, line.number, "cannot mix a mapping into this sequence")

            item_text = line.text[1:].strip()
            if not item_text:
                next_index = index + 1
                child_indent = indent + 2
                if next_index >= len(self.lines):
                    raise _error(self.source, line.number, "sequence item has no value")
                if self.lines[next_index].indent != child_indent:
                    raise _error(
                        self.source,
                        self.lines[next_index].number,
                        f"sequence item must be indented {child_indent} spaces",
                    )
                item, index = self._parse_block(next_index, child_indent)
                result.append(item)
                continue

            if KEY_VALUE_RE.fullmatch(item_text):
                item_mapping: dict[str, Any] = {}
                entry_indent = indent + 2
                index = self._assign_mapping_entry(
                    item_mapping,
                    index,
                    entry_indent,
                    text_override=item_text,
                )
                while index < len(self.lines) and self.lines[index].indent == entry_indent:
                    if self._is_sequence_line(self.lines[index]):
                        raise _error(
                            self.source,
                            self.lines[index].number,
                            "expected a mapping entry for this sequence item",
                        )
                    index = self._assign_mapping_entry(item_mapping, index, entry_indent)
                if index < len(self.lines) and self.lines[index].indent > indent:
                    raise _error(self.source, self.lines[index].number, "unexpected extra indentation")
                result.append(item_mapping)
                continue

            result.append(_parse_scalar(item_text, self.source, line.number))
            index += 1
            if index < len(self.lines) and self.lines[index].indent > indent:
                raise _error(
                    self.source,
                    self.lines[index].number,
                    "scalar sequence items cannot have nested content",
                )

        return result, index


def loads(text: str, source: str = "<string>") -> Any:
    """Parse curriculum YAML text using the controlled subset."""

    return _Parser(_prepare_lines(text, source), source).parse()


def load(path: str | Path) -> Any:
    """Read and parse a UTF-8 curriculum YAML file."""

    yaml_path = Path(path)
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CurriculumYAMLError(f"{yaml_path}: file must be valid UTF-8") from exc
    return loads(text, source=yaml_path.as_posix())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="data/curriculum.yml")
    args = parser.parse_args(argv)

    try:
        load(args.path)
    except (OSError, CurriculumYAMLError) as exc:
        print(f"Curriculum YAML check failed: {exc}", file=sys.stderr)
        return 1

    print(f"Curriculum YAML syntax OK: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
