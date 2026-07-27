#!/usr/bin/env python3
"""Validate the canonical theory coverage map and build its coverage audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from curriculum_yaml import CurriculumYAMLError, load


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_PATH = ROOT / "data" / "theory-coverage.yml"
CURRICULUM_PATH = ROOT / "data" / "curriculum.yml"

SOURCE_ID = "DELTA360-PDF"
SOURCE_URL = (
    "https://www.iekdelta360.edu.gr/files/repository/eoppep/"
    "%CE%99%CE%95%CE%9A-%CE%94%CE%95%CE%9B%CE%A4%CE%91-360-technikos-diktion.pdf"
)
PAGE_COUNT = 151
PAGE_NUMBERING = "pdf_viewer_1_based"
NUMBERED_QUESTION_PAGE_BOUNDS = {"A": (2, 35), "B": (37, 150)}

EXPECTED_GROUPS = {
    "A": {
        "first_id": "A-001",
        "last_id": "A-089",
        "count": 89,
        "source_pages": "2-36",
    },
    "B": {
        "first_id": "B-001",
        "last_id": "B-229",
        "count": 229,
        "source_pages": "37-150",
    },
}
EXPECTED_QUESTION_ID_ORDER = [
    f"A-{number:03d}" for number in range(1, 90)
] + [f"B-{number:03d}" for number in range(1, 230)]
EXPECTED_QUESTION_IDS = set(EXPECTED_QUESTION_ID_ORDER)
# Integrity fixture for the ID -> numbered-question viewer-page map established
# by the independently inspected PDF corpus gate. The canonical records remain
# in data/theory-coverage.yml; this digest prevents silent page drift in CI.
QUESTION_PAGE_MAP_SHA256 = (
    "745305aab23f1aa455944f557cbf6b1f9effc41e85842fda59354a68cc8f3613"
)

TOP_LEVEL_FIELDS = {"source", "chapters", "questions"}
SOURCE_FIELDS = {
    "id",
    "url",
    "page_numbering",
    "page_count",
    "question_groups",
}
GROUP_FIELDS = {"first_id", "last_id", "count", "source_pages"}
QUESTION_FIELDS = {
    "id",
    "group",
    "number",
    "topic_el",
    "domain_id",
    "module_id",
    "chapter_id",
    "source_references",
    "mapping_status",
    "notes",
}
CHAPTER_FIELDS = {
    "id",
    "code",
    "domain_id",
    "module_id",
    "title_el",
    "summary_el",
    "question_ids",
    "source_references",
    "status",
}
REFERENCE_FIELDS = {"source_id", "role", "pages"}
ALLOWED_REFERENCE_ROLES = {"question", "answer", "supporting_material"}
ALLOWED_STATUSES = {"verified", "needs_verification"}

QUESTION_ID_RE = re.compile(r"^([AB])-([0-9]{3})$")
CHAPTER_ID_RE = re.compile(r"^CH-([0-9]{2})-([0-9]{2})-([0-9]{2})$")
CHAPTER_CODE_RE = re.compile(r"^([0-9]{2})\.([0-9]{2})\.([0-9]{2})$")
PAGE_RE = re.compile(r"^([1-9][0-9]*)(?:-([1-9][0-9]*))?$")
GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")


def _exact_fields(
    value: Any,
    expected: set[str],
    label: str,
    errors: list[str],
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a mapping")
        return False
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        errors.append(f"{label} is missing fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"{label} has unknown fields: {', '.join(unknown)}")
    return not missing


def _nonempty_greek(value: Any, label: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return False
    if value != value.strip():
        errors.append(f"{label} must not have leading or trailing whitespace")
    if not GREEK_RE.search(value):
        errors.append(f"{label} must contain Greek text")
        return False
    return True


def _topic_description(value: Any, label: str, errors: list[str]) -> None:
    if not _nonempty_greek(value, label, errors):
        return
    if "\n" in value or "\r" in value:
        errors.append(f"{label} must be a single-line topic description")
    greek_letter_count = len(GREEK_RE.findall(value))
    if len(value) < 8 or greek_letter_count < 4:
        errors.append(f"{label} must be a meaningful concise Greek description")
    if len(value) > 120:
        errors.append(
            f"{label} must be concise and no longer than 120 characters"
        )


def _reference_page_set(reference: dict[str, Any]) -> set[tuple[str, int]]:
    pages = reference.get("pages")
    role = reference.get("role")
    if not isinstance(pages, str) or not isinstance(role, str):
        return set()
    match = PAGE_RE.fullmatch(pages)
    if not match:
        return set()
    endpoint_texts = (match.group(1), match.group(2) or match.group(1))
    if any(len(value) > len(str(PAGE_COUNT)) for value in endpoint_texts):
        return set()
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    if start < 1 or start > end or end > PAGE_COUNT:
        return set()
    return {(role, page) for page in range(start, end + 1)}


def _validate_references(
    value: Any,
    label: str,
    page_count: int,
    errors: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty list")
        return []

    valid_mappings: list[dict[str, Any]] = []
    for index, reference in enumerate(value, start=1):
        reference_label = f"{label}[{index}]"
        if not _exact_fields(
            reference, REFERENCE_FIELDS, reference_label, errors
        ):
            continue
        valid_mappings.append(reference)

        if reference.get("source_id") != SOURCE_ID:
            errors.append(
                f"{reference_label}.source_id must be the sole source {SOURCE_ID}"
            )

        role = reference.get("role")
        if not isinstance(role, str) or role not in ALLOWED_REFERENCE_ROLES:
            errors.append(
                f"{reference_label}.role must be one of "
                f"{', '.join(sorted(ALLOWED_REFERENCE_ROLES))}"
            )

        pages = reference.get("pages")
        if not isinstance(pages, str):
            errors.append(f"{reference_label}.pages must be a string")
            continue
        match = PAGE_RE.fullmatch(pages)
        if not match:
            numeric_range = re.fullmatch(r"([0-9]+)(?:-([0-9]+))?", pages)
            if numeric_range and (
                int(numeric_range.group(1)) == 0
                or int(numeric_range.group(2) or numeric_range.group(1)) == 0
            ):
                errors.append(
                    f"{reference_label}.pages uses a zero-based page reference"
                )
            else:
                errors.append(
                    f"{reference_label}.pages has malformed page reference {pages!r}"
                )
            continue

        endpoint_texts = (match.group(1), match.group(2) or match.group(1))
        if any(
            len(value) > len(str(page_count)) for value in endpoint_texts
        ):
            errors.append(
                f"{reference_label}.pages exceeds PDF viewer page count {page_count}"
            )
            continue
        start = int(endpoint_texts[0])
        end = int(endpoint_texts[1])
        if start < 1:
            errors.append(f"{reference_label}.pages must begin at page 1 or later")
        if start > end:
            errors.append(f"{reference_label}.pages has a reversed page range")
        if end > page_count:
            errors.append(
                f"{reference_label}.pages exceeds PDF viewer page count {page_count}"
            )

    return valid_mappings


def _curriculum_indexes(
    curriculum: Any, errors: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    if not isinstance(curriculum, dict):
        errors.append("curriculum root must be a mapping")
        return [], [], {}, {}
    domains = curriculum.get("domains")
    modules = curriculum.get("modules")
    if not isinstance(domains, list):
        errors.append("curriculum domains must be a list")
        domains = []
    if not isinstance(modules, list):
        errors.append("curriculum modules must be a list")
        modules = []
    domain_by_id = {
        domain.get("id"): domain
        for domain in domains
        if isinstance(domain, dict) and isinstance(domain.get("id"), str)
    }
    module_by_id = {
        module.get("id"): module
        for module in modules
        if isinstance(module, dict) and isinstance(module.get("id"), str)
    }
    if len(domain_by_id) != 10:
        errors.append("canonical curriculum must contain exactly 10 domains")
    if len(module_by_id) != 24:
        errors.append("canonical curriculum must contain exactly 24 modules")
    return domains, modules, domain_by_id, module_by_id


def validate_theory_coverage(coverage: Any, curriculum: Any) -> list[str]:
    """Return every validation error for parsed coverage and curriculum data."""

    errors: list[str] = []
    domains, modules, domain_by_id, module_by_id = _curriculum_indexes(
        curriculum, errors
    )

    if not _exact_fields(coverage, TOP_LEVEL_FIELDS, "coverage root", errors):
        return errors

    source = coverage.get("source")
    if _exact_fields(source, SOURCE_FIELDS, "source", errors):
        if source.get("id") != SOURCE_ID:
            errors.append(f"source.id must be {SOURCE_ID}")
        if source.get("url") != SOURCE_URL:
            errors.append("source.url must match the sole knowledge-source URL")
        if source.get("page_numbering") != PAGE_NUMBERING:
            errors.append(f"source.page_numbering must be {PAGE_NUMBERING}")
        page_count = source.get("page_count")
        if type(page_count) is not int or page_count <= 0:
            errors.append("source.page_count must be a positive integer")
            page_count = PAGE_COUNT
        elif page_count != PAGE_COUNT:
            errors.append(
                f"source.page_count must equal the verified PDF page count {PAGE_COUNT}"
            )

        groups = source.get("question_groups")
        if not isinstance(groups, dict):
            errors.append("source.question_groups must be a mapping")
        else:
            if set(groups) != set(EXPECTED_GROUPS):
                errors.append("source.question_groups must contain exactly A and B")
            for group, expected in EXPECTED_GROUPS.items():
                metadata = groups.get(group)
                label = f"source.question_groups.{group}"
                if not _exact_fields(metadata, GROUP_FIELDS, label, errors):
                    continue
                for field, expected_value in expected.items():
                    if metadata.get(field) != expected_value:
                        errors.append(
                            f"{label}.{field} must be {expected_value!r}"
                        )
    else:
        page_count = PAGE_COUNT

    chapters = coverage.get("chapters")
    questions = coverage.get("questions")
    if not isinstance(chapters, list):
        errors.append("chapters must be a list")
        chapters = []
    if not isinstance(questions, list):
        errors.append("questions must be a list")
        questions = []

    chapter_by_id: dict[str, dict[str, Any]] = {}
    chapter_ids: list[str] = []
    chapter_codes: list[str] = []
    chapter_numbers_by_module: dict[str, list[int]] = defaultdict(list)
    valid_chapter_records: list[dict[str, Any]] = []

    for index, chapter in enumerate(chapters, start=1):
        label = f"chapters[{index}]"
        if not _exact_fields(chapter, CHAPTER_FIELDS, label, errors):
            continue
        valid_chapter_records.append(chapter)
        chapter_id = chapter.get("id")
        code = chapter.get("code")
        domain_id = chapter.get("domain_id")
        module_id = chapter.get("module_id")

        if not isinstance(chapter_id, str) or not CHAPTER_ID_RE.fullmatch(
            chapter_id
        ):
            errors.append(f"{label}.id has invalid chapter ID format")
        else:
            chapter_ids.append(chapter_id)
            chapter_by_id.setdefault(chapter_id, chapter)
        if not isinstance(code, str) or not CHAPTER_CODE_RE.fullmatch(code):
            errors.append(f"{label}.code has invalid chapter code format")
        else:
            chapter_codes.append(code)

        id_match = (
            CHAPTER_ID_RE.fullmatch(chapter_id)
            if isinstance(chapter_id, str)
            else None
        )
        code_match = (
            CHAPTER_CODE_RE.fullmatch(code) if isinstance(code, str) else None
        )
        if id_match and code_match and id_match.groups() != code_match.groups():
            errors.append(f"{label}: chapter ID/code mismatch")

        if not isinstance(domain_id, str) or domain_id not in domain_by_id:
            errors.append(f"{label}.domain_id references an unknown domain")
        if not isinstance(module_id, str) or module_id not in module_by_id:
            errors.append(f"{label}.module_id references an unknown module")
        elif module_by_id[module_id].get("domain_id") != domain_id:
            errors.append(f"{label}: module/domain ownership mismatch")

        if (
            code_match
            and isinstance(module_id, str)
            and module_id in module_by_id
        ):
            display_code = module_by_id[module_id].get("display_code")
            prefix = ".".join(code_match.groups()[:2])
            if prefix != display_code:
                errors.append(
                    f"{label}: chapter code prefix does not match module display code"
                )
            chapter_numbers_by_module[module_id].append(int(code_match.group(3)))

        _nonempty_greek(chapter.get("title_el"), f"{label}.title_el", errors)
        _nonempty_greek(chapter.get("summary_el"), f"{label}.summary_el", errors)

        question_ids = chapter.get("question_ids")
        if not isinstance(question_ids, list) or not question_ids:
            errors.append(f"{label}.question_ids must be a non-empty list")
        elif any(
            not isinstance(question_id, str) or not question_id
            for question_id in question_ids
        ):
            errors.append(f"{label}.question_ids must contain only non-empty IDs")
        elif len(question_ids) != len(set(question_ids)):
            errors.append(f"{label}.question_ids contains a duplicate question")

        _validate_references(
            chapter.get("source_references"),
            f"{label}.source_references",
            page_count,
            errors,
        )

        status = chapter.get("status")
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            errors.append(f"{label}.status has unsupported status {status!r}")
        elif status == "verified":
            errors.append(f"{label}: newly created verified chapter is not allowed")

    duplicate_chapter_ids = sorted(
        value for value, count in Counter(chapter_ids).items() if count > 1
    )
    duplicate_chapter_codes = sorted(
        value for value, count in Counter(chapter_codes).items() if count > 1
    )
    if duplicate_chapter_ids:
        errors.append(
            "duplicate chapter ID(s): " + ", ".join(duplicate_chapter_ids)
        )
    if duplicate_chapter_codes:
        errors.append(
            "duplicate chapter code(s): " + ", ".join(duplicate_chapter_codes)
        )

    for module_id, numbers in sorted(chapter_numbers_by_module.items()):
        unique_numbers = sorted(set(numbers))
        if unique_numbers and unique_numbers[0] != 1:
            errors.append(f"{module_id}: chapter numbering must begin at 01")
        expected_numbers = list(range(1, len(unique_numbers) + 1))
        if unique_numbers != expected_numbers:
            errors.append(f"{module_id}: chapter numbering must be continuous")

    question_by_id: dict[str, dict[str, Any]] = {}
    question_ids: list[str] = []
    question_pages_by_id: dict[str, tuple[int, ...]] = {}
    valid_question_records: list[dict[str, Any]] = []

    for index, question in enumerate(questions, start=1):
        label = f"questions[{index}]"
        if not _exact_fields(question, QUESTION_FIELDS, label, errors):
            continue
        valid_question_records.append(question)
        question_id = question.get("id")
        group = question.get("group")
        number = question.get("number")
        domain_id = question.get("domain_id")
        module_id = question.get("module_id")
        chapter_id = question.get("chapter_id")

        match = (
            QUESTION_ID_RE.fullmatch(question_id)
            if isinstance(question_id, str)
            else None
        )
        if not match:
            errors.append(f"{label}.id has invalid question ID format")
        else:
            question_ids.append(question_id)
            question_by_id.setdefault(question_id, question)
            if group != match.group(1):
                errors.append(f"{label}: ID/group mismatch")
            if type(number) is not int or number != int(match.group(2)):
                errors.append(f"{label}: ID/number mismatch")

        if not isinstance(group, str) or group not in EXPECTED_GROUPS:
            errors.append(f"{label}.group must be A or B")
        if type(number) is not int or number <= 0:
            errors.append(f"{label}.number must be a positive integer")

        _topic_description(question.get("topic_el"), f"{label}.topic_el", errors)

        if not isinstance(domain_id, str) or domain_id not in domain_by_id:
            errors.append(f"{label}.domain_id references an unknown domain")
        if not isinstance(module_id, str) or module_id not in module_by_id:
            errors.append(f"{label}.module_id references an unknown module")
        elif module_by_id[module_id].get("domain_id") != domain_id:
            errors.append(f"{label}: module/domain ownership mismatch")

        if not isinstance(chapter_id, str) or not chapter_id:
            errors.append(f"{label}.chapter_id must name exactly one chapter")
        elif chapter_id not in chapter_by_id:
            errors.append(f"{label}.chapter_id references a missing chapter")
        else:
            chapter = chapter_by_id[chapter_id]
            if (
                chapter.get("domain_id") != domain_id
                or chapter.get("module_id") != module_id
            ):
                errors.append(f"{label}: question/chapter ownership mismatch")

        references = _validate_references(
            question.get("source_references"),
            f"{label}.source_references",
            page_count,
            errors,
        )
        if references and not any(
            reference.get("role") == "question" for reference in references
        ):
            errors.append(
                f"{label}.source_references must include role 'question'"
            )
        question_pages = {
            page
            for reference in references
            if reference.get("role") == "question"
            for _role, page in _reference_page_set(reference)
        }
        if (
            isinstance(question_id, str)
            and isinstance(group, str)
            and group in NUMBERED_QUESTION_PAGE_BOUNDS
            and question_pages
        ):
            minimum, maximum = NUMBERED_QUESTION_PAGE_BOUNDS[group]
            if any(
                page < minimum or page > maximum for page in question_pages
            ):
                errors.append(
                    f"{label}.source_references places a Group {group} "
                    "question outside its verified viewer-page range"
                )
            if len(question_pages) != 1:
                errors.append(
                    f"{label}.source_references must identify exactly one "
                    "numbered-question viewer page"
                )
            question_pages_by_id[question_id] = tuple(sorted(question_pages))

        status = question.get("mapping_status")
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            errors.append(
                f"{label}.mapping_status has unsupported status {status!r}"
            )
        elif status == "verified":
            errors.append(
                f"{label}: newly created verified question mapping is not allowed"
            )

        notes = question.get("notes")
        if notes is not None and not isinstance(notes, str):
            errors.append(f"{label}.notes must be null or a string")
        elif isinstance(notes, str) and not notes.strip():
            errors.append(f"{label}.notes must be null instead of an empty string")

    duplicate_question_ids = sorted(
        value for value, count in Counter(question_ids).items() if count > 1
    )
    if duplicate_question_ids:
        errors.append(
            "duplicate question ID(s): " + ", ".join(duplicate_question_ids)
        )

    actual_question_ids = set(question_ids)
    missing_question_ids = sorted(EXPECTED_QUESTION_IDS - actual_question_ids)
    unexpected_question_ids = sorted(actual_question_ids - EXPECTED_QUESTION_IDS)
    if missing_question_ids:
        errors.append(
            "missing expected question ID(s): " + ", ".join(missing_question_ids)
        )
    if unexpected_question_ids:
        errors.append(
            "unexpected question ID(s): " + ", ".join(unexpected_question_ids)
        )

    actual_group_counts = Counter(
        question.get("group")
        for question in valid_question_records
        if isinstance(question.get("group"), str)
        and question.get("group") in EXPECTED_GROUPS
    )
    for group, expected in EXPECTED_GROUPS.items():
        if actual_group_counts[group] != expected["count"]:
            errors.append(
                f"Group {group} must contain exactly {expected['count']} questions"
            )
    if len(valid_question_records) != 318:
        errors.append("coverage must contain exactly 318 question records")

    for group in EXPECTED_GROUPS:
        ordered_pages = [
            question_pages_by_id.get(f"{group}-{number:03d}")
            for number in range(
                1, EXPECTED_GROUPS[group]["count"] + 1
            )
        ]
        if all(pages is not None and len(pages) == 1 for pages in ordered_pages):
            page_numbers = [pages[0] for pages in ordered_pages if pages]
            if page_numbers != sorted(page_numbers):
                errors.append(
                    f"Group {group} numbered-question pages must be non-decreasing"
                )

    if (
        set(question_pages_by_id) == EXPECTED_QUESTION_IDS
        and all(len(pages) == 1 for pages in question_pages_by_id.values())
    ):
        page_payload = "".join(
            f"{question_id}:{question_pages_by_id[question_id][0]}\n"
            for question_id in EXPECTED_QUESTION_ID_ORDER
        )
        page_digest = hashlib.sha256(page_payload.encode("utf-8")).hexdigest()
        if page_digest != QUESTION_PAGE_MAP_SHA256:
            errors.append(
                "question-to-viewer-page map does not match the audited PDF corpus"
            )

    listed_by: dict[str, list[str]] = defaultdict(list)
    for chapter in valid_chapter_records:
        chapter_id = chapter.get("id")
        question_id_list = chapter.get("question_ids")
        if not isinstance(chapter_id, str) or not isinstance(
            question_id_list, list
        ):
            continue
        for question_id in question_id_list:
            if not isinstance(question_id, str):
                continue
            listed_by[question_id].append(chapter_id)
            if question_id not in question_by_id:
                errors.append(
                    f"{chapter_id}: chapter lists unknown question {question_id}"
                )
            elif question_by_id[question_id].get("chapter_id") != chapter_id:
                errors.append(
                    f"{chapter_id}/{question_id}: non-reciprocal chapter relationship"
                )

    for question_id, question in question_by_id.items():
        assigned_chapter = question.get("chapter_id")
        owners = listed_by.get(question_id, [])
        if not owners:
            errors.append(f"{question_id}: orphaned question is not listed by a chapter")
        elif owners.count(assigned_chapter) != 1:
            errors.append(
                f"{question_id}: assigned chapter relationship is non-reciprocal"
            )
        if len(owners) > 1:
            errors.append(
                f"{question_id}: question is listed by multiple chapters"
            )

    for chapter in valid_chapter_records:
        chapter_id = chapter.get("id")
        question_id_list = chapter.get("question_ids")
        chapter_references = chapter.get("source_references")
        if not isinstance(question_id_list, list) or not isinstance(
            chapter_references, list
        ):
            continue
        expected_pages: set[tuple[str, int]] = set()
        all_questions_found = True
        for question_id in question_id_list:
            question = question_by_id.get(question_id)
            if not question:
                all_questions_found = False
                continue
            references = question.get("source_references")
            if not isinstance(references, list):
                all_questions_found = False
                continue
            for reference in references:
                if isinstance(reference, dict):
                    expected_pages.update(_reference_page_set(reference))
        actual_pages: set[tuple[str, int]] = set()
        for reference in chapter_references:
            if isinstance(reference, dict):
                actual_pages.update(_reference_page_set(reference))
        if all_questions_found and expected_pages != actual_pages:
            errors.append(
                f"{chapter_id}: chapter source references must equal the "
                "assigned-question page union"
            )

    question_count_by_module = Counter(
        question.get("module_id")
        for question in valid_question_records
        if isinstance(question.get("module_id"), str)
        and question.get("module_id") in module_by_id
    )
    chapter_count_by_module = Counter(
        chapter.get("module_id")
        for chapter in valid_chapter_records
        if isinstance(chapter.get("module_id"), str)
        and chapter.get("module_id") in module_by_id
    )
    for module in modules:
        if not isinstance(module, dict):
            continue
        module_id = module.get("id")
        if not isinstance(module_id, str):
            continue
        question_count = question_count_by_module[module_id]
        chapter_count = chapter_count_by_module[module_id]
        if question_count and not chapter_count:
            errors.append(
                f"{module_id}: mapped questions require at least one chapter"
            )
        if not question_count and chapter_count:
            errors.append(
                f"{module_id}: zero-coverage module must not have artificial chapters"
            )

    domain_question_total = sum(
        1
        for question in valid_question_records
        if isinstance(question.get("domain_id"), str)
        and question.get("domain_id") in domain_by_id
    )
    module_question_total = sum(question_count_by_module.values())
    if domain_question_total != module_question_total:
        errors.append("domain and module question totals do not reconcile")

    return errors


def build_coverage_audit(coverage: dict[str, Any], curriculum: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic coverage totals for validation and report generation."""

    domains = curriculum["domains"]
    modules = curriculum["modules"]
    questions = coverage["questions"]
    chapters = coverage["chapters"]

    question_count_by_domain = Counter(
        question["domain_id"] for question in questions
    )
    question_count_by_module = Counter(
        question["module_id"] for question in questions
    )
    chapter_count_by_domain = Counter(chapter["domain_id"] for chapter in chapters)
    chapter_count_by_module = Counter(chapter["module_id"] for chapter in chapters)
    question_statuses = Counter(
        question["mapping_status"] for question in questions
    )
    chapter_statuses = Counter(chapter["status"] for chapter in chapters)

    page_values: list[int] = []
    for question in questions:
        for reference in question["source_references"]:
            if reference["role"] != "question":
                continue
            page_values.extend(
                page
                for _role, page in _reference_page_set(reference)
            )

    module_ids = [module["id"] for module in modules]
    covered_modules = [
        module_id
        for module_id in module_ids
        if question_count_by_module[module_id] > 0
    ]
    zero_coverage_modules = [
        module_id
        for module_id in module_ids
        if question_count_by_module[module_id] == 0
    ]

    return {
        "group_counts": {
            group: sum(1 for question in questions if question["group"] == group)
            for group in EXPECTED_GROUPS
        },
        "total_question_count": len(questions),
        "total_chapter_count": len(chapters),
        "question_count_by_domain": {
            domain["id"]: question_count_by_domain[domain["id"]]
            for domain in domains
        },
        "question_count_by_module": {
            module["id"]: question_count_by_module[module["id"]]
            for module in modules
        },
        "chapter_count_by_domain": {
            domain["id"]: chapter_count_by_domain[domain["id"]]
            for domain in domains
        },
        "chapter_count_by_module": {
            module["id"]: chapter_count_by_module[module["id"]]
            for module in modules
        },
        "covered_modules": covered_modules,
        "zero_coverage_modules": zero_coverage_modules,
        "question_statuses": {
            status: question_statuses[status] for status in sorted(ALLOWED_STATUSES)
        },
        "chapter_statuses": {
            status: chapter_statuses[status] for status in sorted(ALLOWED_STATUSES)
        },
        "ambiguity_question_ids": [
            question["id"]
            for question in questions
            if isinstance(question["notes"], str) and question["notes"].strip()
        ],
        "source_page_minimum": min(page_values) if page_values else None,
        "source_page_maximum": max(page_values) if page_values else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit",
        action="store_true",
        help="print the structured coverage audit after successful validation",
    )
    args = parser.parse_args(argv)

    try:
        curriculum = load(CURRICULUM_PATH)
        coverage = load(COVERAGE_PATH)
    except (OSError, CurriculumYAMLError) as exc:
        print(f"Theory coverage validation failed: {exc}", file=sys.stderr)
        return 1

    errors = validate_theory_coverage(coverage, curriculum)
    if errors:
        print("Theory coverage validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    audit = build_coverage_audit(coverage, curriculum)
    if args.audit:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(
        "Theory coverage OK: "
        f"Group A={audit['group_counts']['A']}, "
        f"Group B={audit['group_counts']['B']}, "
        f"total questions={audit['total_question_count']}, "
        f"chapters={audit['total_chapter_count']}, "
        f"covered modules={len(audit['covered_modules'])}, "
        f"zero-coverage modules={len(audit['zero_coverage_modules'])}, "
        "question statuses "
        f"verified={audit['question_statuses']['verified']}, "
        "needs_verification="
        f"{audit['question_statuses']['needs_verification']}; "
        "chapter statuses "
        f"verified={audit['chapter_statuses']['verified']}, "
        "needs_verification="
        f"{audit['chapter_statuses']['needs_verification']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
