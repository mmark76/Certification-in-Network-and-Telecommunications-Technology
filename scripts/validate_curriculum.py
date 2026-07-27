#!/usr/bin/env python3
"""Validate canonical curriculum structure, references and projections."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any

from curriculum_yaml import CurriculumYAMLError, load
from generate_curriculum_data import render_curriculum_data


ROOT = Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "data" / "curriculum.yml"
GENERATED_DATA = ROOT / "assets" / "curriculum-data.js"

ALLOWED_STATUSES = {
    "planned",
    "draft",
    "needs_verification",
    "reviewed",
    "practiced",
    "complete",
}
REVIEWED_STATUSES = {"reviewed", "practiced", "complete"}
DOMAIN_ID_RE = re.compile(r"^DOMAIN-(?:0[1-9]|10)$")
MODULE_ID_RE = re.compile(r"^MOD-(?:0[1-9]|1[0-9]|2[0-4])$")
DISPLAY_CODE_RE = re.compile(
    r"^(?P<domain>0[1-9]|10)\.(?P<module>0[1-9]|[1-9][0-9])$"
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
QUESTION_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}-[0-9]{3}$")
FLASHCARD_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}-[0-9]{3}$")
LAB_ID_RE = re.compile(r"^LAB-[A-Z][A-Z0-9]{1,7}-[0-9]{3}$")

EXPECTED_DOMAIN_DEFINITIONS = (
    (
        "DOMAIN-01",
        1,
        "Ψηφιακή πληροφορία και λογική",
        "Πώς αναπαριστά ο υπολογιστής την πληροφορία;",
        ("MOD-01",),
    ),
    (
        "DOMAIN-02",
        2,
        "Αρχιτεκτονική και υλικό υπολογιστών",
        "Πώς λειτουργεί και από τι αποτελείται ένας υπολογιστής;",
        ("MOD-02", "MOD-17", "MOD-18"),
    ),
    (
        "DOMAIN-03",
        3,
        "Λειτουργικά συστήματα και διαχείριση",
        "Πώς διαχειρίζεται το λειτουργικό το υλικό, τα αρχεία και τους χρήστες;",
        ("MOD-03", "MOD-23"),
    ),
    (
        "DOMAIN-04",
        4,
        "Αλγόριθμοι και προγραμματισμός",
        "Πώς περιγράφουμε και υλοποιούμε μία υπολογιστική λύση;",
        ("MOD-19", "MOD-20"),
    ),
    (
        "DOMAIN-05",
        5,
        "Εφαρμογές και πληροφοριακά συστήματα",
        "Πώς οργανώνεται και χρησιμοποιείται η πληροφορία στην πράξη;",
        ("MOD-21", "MOD-22"),
    ),
    (
        "DOMAIN-06",
        6,
        "Θεμέλια δικτύων",
        "Πώς επικοινωνούν δύο συσκευές στο ίδιο ή σε διαφορετικά δίκτυα;",
        ("MOD-04", "MOD-05"),
    ),
    (
        "DOMAIN-07",
        7,
        "IP, μεταγωγή και δρομολόγηση",
        "Πώς βρίσκει ένα πακέτο τον προορισμό του;",
        ("MOD-06", "MOD-07", "MOD-08"),
    ),
    (
        "DOMAIN-08",
        8,
        "Υπηρεσίες και διαχείριση δικτύου",
        "Ποιες υπηρεσίες κάνουν ένα δίκτυο λειτουργικό και διαχειρίσιμο;",
        ("MOD-09", "MOD-11"),
    ),
    (
        "DOMAIN-09",
        9,
        "Μετάδοση και τηλεπικοινωνίες",
        (
            "Πώς μεταφέρεται φυσικά ένα σήμα και πώς λειτουργούν τα "
            "τηλεπικοινωνιακά δίκτυα;"
        ),
        ("MOD-10", "MOD-12", "MOD-13", "MOD-24"),
    ),
    (
        "DOMAIN-10",
        10,
        "Ασφάλεια και αντιμετώπιση προβλημάτων",
        "Πώς προστατεύουμε, ελέγχουμε και αποκαθιστούμε ένα σύστημα;",
        ("MOD-14", "MOD-15", "MOD-16"),
    ),
)
EXPECTED_DOMAINS = {
    domain_id: {
        "order": order,
        "title": title,
        "guiding_question": guiding_question,
        "module_ids": module_ids,
    }
    for (
        domain_id,
        order,
        title,
        guiding_question,
        module_ids,
    ) in EXPECTED_DOMAIN_DEFINITIONS
}
EXPECTED_MODULE_IDS = {f"MOD-{number:02d}" for number in range(1, 25)}
EXPECTED_MODULE_DOMAINS = {
    module_id: domain_id
    for domain_id, definition in EXPECTED_DOMAINS.items()
    for module_id in definition["module_ids"]
}
EXPECTED_MODULE_DISPLAY_CODES = {
    "MOD-01": "01.01",
    "MOD-02": "02.01",
    "MOD-03": "03.01",
    "MOD-04": "06.01",
    "MOD-05": "06.02",
    "MOD-06": "07.01",
    "MOD-07": "07.02",
    "MOD-08": "07.03",
    "MOD-09": "08.01",
    "MOD-10": "09.01",
    "MOD-11": "08.02",
    "MOD-12": "09.02",
    "MOD-13": "09.03",
    "MOD-14": "10.01",
    "MOD-15": "10.02",
    "MOD-16": "10.03",
    "MOD-17": "02.02",
    "MOD-18": "02.03",
    "MOD-19": "04.01",
    "MOD-20": "04.02",
    "MOD-21": "05.01",
    "MOD-22": "05.02",
    "MOD-23": "03.02",
    "MOD-24": "09.04",
}
EXPECTED_NEW_MODULE_TITLES = {
    "MOD-17": "Μνήμες, αποθήκευση και περιφερειακές συσκευές",
    "MOD-18": "Ψηφιακά ηλεκτρονικά και ενσωματωμένα συστήματα",
    "MOD-19": "Αλγόριθμοι και δομές δεδομένων",
    "MOD-20": "Γλώσσες προγραμματισμού, Pascal και Assembly",
    "MOD-21": "Εφαρμογές γραφείου και λογιστικά φύλλα",
    "MOD-22": "Δεδομένα και πληροφοριακά συστήματα",
    "MOD-23": "Διαχείριση συστημάτων, χρηστών και αντιγράφων ασφαλείας",
    "MOD-24": "Κινητές επικοινωνίες και κυψελωτά δίκτυα",
}

TOP_LEVEL_FIELDS = {
    "version",
    "last_updated",
    "domains",
    "questions",
    "flashcards",
    "labs",
    "modules",
}
DOMAIN_FIELDS = {
    "id",
    "order",
    "title",
    "guiding_question",
    "module_ids",
}
MODULE_REQUIRED_FIELDS = {
    "id",
    "order",
    "display_code",
    "domain_id",
    "slug",
    "title_el",
    "syllabus_area",
    "status",
    "available",
    "lesson",
    "questions",
    "flashcards",
    "labs",
    "source_references",
    "last_verified",
}
MODULE_ALLOWED_FIELDS = MODULE_REQUIRED_FIELDS | {"reviewer"}
QUESTION_FIELDS = {"id", "html", "module_id"}
FLASHCARD_REQUIRED_FIELDS = {"id", "html", "module_id"}
FLASHCARD_FIELDS = FLASHCARD_REQUIRED_FIELDS | {"markdown"}
LAB_FIELDS = {"id", "markdown", "html", "module_id"}

REQUIRED_FILES = (
    ".gitignore",
    ".nojekyll",
    "AGENTS.md",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/pages.yml",
    ".github/workflows/quality.yml",
    "data/curriculum.yml",
    "docs/INDEX.md",
    "docs/TRACEABILITY_MATRIX.md",
    "docs/product/PROJECT_BRIEF.md",
    "syllabus/README.md",
    "theory/README.md",
    "theory/01-digital-logic-and-number-systems.md",
    "questions/README.md",
    "questions/MOD-01-flashcards.md",
    "practical/README.md",
    "practical/LAB-GEN-001-binary-and-logic.md",
    "progress/STUDY_PLAN.md",
    "resources/KNOWLEDGE_SOURCE.md",
    "index.html",
    "curriculum.html",
    "lesson-digital-logic.html",
    "practice-binary.html",
    "assets/app.js",
    "assets/flashcards.css",
    "assets/flashcards.js",
    "assets/styles.css",
    "assets/fixed-layout.css",
    "assets/interface-overrides.css",
    "assets/curriculum-data.js",
    "scripts/curriculum_yaml.py",
    "scripts/validate_curriculum.py",
    "scripts/check_html_ids.py",
    "scripts/check_internal_links.py",
    "scripts/generate_curriculum_data.py",
    "scripts/test_curriculum_display_codes.py",
    "scripts/test_progress.mjs",
)


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.question_ids: list[tuple[str, int]] = []
        self.flashcard_ids: list[tuple[str, int]] = []
        self.render_hosts: dict[str, list[int]] = defaultdict(list)

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del tag
        attributes = dict(attrs)
        line = self.getpos()[0]
        if "data-question-id" in attributes:
            self.question_ids.append((attributes["data-question-id"] or "", line))
        if "data-flashcard-id" in attributes:
            self.flashcard_ids.append((attributes["data-flashcard-id"] or "", line))
        for attribute in (
            "data-domain-navigation",
            "data-curriculum-domains",
            "data-home-domains",
        ):
            if attribute in attributes:
                self.render_hosts[attribute].append(line)


def _display(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _check_fields(
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
    context: str,
    errors: list[str],
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - allowed)
    if missing:
        errors.append(f"{context}: missing field(s): {', '.join(missing)}")
    if unknown:
        errors.append(f"{context}: unknown field(s): {', '.join(unknown)}")


def _parse_date(value: Any, context: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{context}: expected an ISO date string (YYYY-MM-DD)")
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        errors.append(f"{context}: invalid ISO date {value!r}")
        return None
    if parsed.isoformat() != value:
        errors.append(f"{context}: date must use canonical YYYY-MM-DD form")
        return None
    return parsed


def _safe_file(
    value: Any,
    context: str,
    errors: list[str],
    suffix: str | None = None,
) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        errors.append(f"{context}: path must be a non-empty string or null")
        return None
    if "\\" in value:
        errors.append(f"{context}: path must use '/' separators")
        return None
    if re.match(r"^[A-Za-z]:", value):
        errors.append(f"{context}: absolute paths are not allowed")
        return None

    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        errors.append(f"{context}: path must stay within the repository")
        return None

    resolved = (ROOT / Path(*relative.parts)).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        errors.append(f"{context}: resolved path escapes the repository")
        return None

    if suffix and resolved.suffix.lower() != suffix:
        errors.append(f"{context}: expected a {suffix} file, found {value!r}")
    if not resolved.is_file():
        errors.append(f"{context}: file does not exist: {value}")
    return resolved


def _string_list(
    value: Any,
    context: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{context}: expected a list")
        return []
    strings: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{context}[{index}]: expected a non-empty string")
            continue
        strings.append(item)
    duplicates = sorted(item for item, count in Counter(strings).items() if count > 1)
    if duplicates:
        errors.append(f"{context}: duplicate value(s): {', '.join(duplicates)}")
    return strings


def _load_html_metadata(
    errors: list[str],
) -> dict[Path, MetadataParser]:
    parsed: dict[Path, MetadataParser] = {}
    for path in sorted(ROOT.rglob("*.html")):
        if ".git" in path.relative_to(ROOT).parts:
            continue
        resolved = path.resolve()
        parser = MetadataParser()
        try:
            parser.feed(resolved.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{_display(resolved)}: cannot read valid UTF-8 HTML: {exc}")
            continue
        parsed[resolved] = parser
    return parsed


def _validate_domains(
    domains_value: Any,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    domains_by_id: dict[str, dict[str, Any]] = {}

    if not isinstance(domains_value, list):
        errors.append("domains: expected a list")
        return domains_by_id
    if len(domains_value) != 10:
        errors.append(f"domains: expected exactly 10 entries, found {len(domains_value)}")

    orders: list[int] = []
    for index, domain in enumerate(domains_value):
        context = f"domains[{index}]"
        if not isinstance(domain, dict):
            errors.append(f"{context}: expected a mapping")
            continue
        _check_fields(domain, DOMAIN_FIELDS, DOMAIN_FIELDS, context, errors)

        domain_id = domain.get("id")
        if not isinstance(domain_id, str) or not DOMAIN_ID_RE.fullmatch(domain_id):
            errors.append(f"{context}.id: expected DOMAIN-01 through DOMAIN-10")
        else:
            if domain_id in domains_by_id:
                errors.append(f"{context}.id: duplicate domain ID {domain_id}")
            domains_by_id[domain_id] = domain

        order = domain.get("order")
        if type(order) is not int or not 1 <= order <= 10:
            errors.append(f"{context}.order: expected an integer from 1 through 10")
        else:
            orders.append(order)

        title = domain.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{context}.title: expected a non-empty string")

        guiding_question = domain.get("guiding_question")
        if not isinstance(guiding_question, str) or not guiding_question.strip():
            errors.append(f"{context}.guiding_question: expected a non-empty string")

        module_ids = _string_list(
            domain.get("module_ids"),
            f"{context}.module_ids",
            errors,
        )
        if not module_ids:
            errors.append(f"{context}.module_ids: expected at least one module")
        for module_id in module_ids:
            if module_id not in EXPECTED_MODULE_IDS:
                errors.append(
                    f"{context}.module_ids: unknown canonical module {module_id!r}"
                )

        expected = (
            EXPECTED_DOMAINS.get(domain_id)
            if isinstance(domain_id, str)
            else None
        )
        if expected is not None:
            if order != expected["order"]:
                errors.append(
                    f"{domain_id}.order: expected {expected['order']}, found {order!r}"
                )
            if title != expected["title"]:
                errors.append(f"{domain_id}.title: must match the canonical title")
            if guiding_question != expected["guiding_question"]:
                errors.append(
                    f"{domain_id}.guiding_question: must match the canonical "
                    "retrieval cue"
                )
            if module_ids != list(expected["module_ids"]):
                expected_modules = ", ".join(expected["module_ids"])
                errors.append(
                    f"{domain_id}.module_ids: expected [{expected_modules}] "
                    "in this order"
                )

    duplicate_orders = sorted(
        str(value) for value, count in Counter(orders).items() if count > 1
    )
    if duplicate_orders:
        errors.append(f"domains: duplicate order(s): {', '.join(duplicate_orders)}")
    if set(orders) != set(range(1, 11)):
        errors.append("domains: orders must be exactly 1 through 10")

    expected_ids = set(EXPECTED_DOMAINS)
    actual_ids = set(domains_by_id)
    missing_ids = sorted(expected_ids - actual_ids)
    extra_ids = sorted(actual_ids - expected_ids)
    if missing_ids:
        errors.append(f"domains: missing canonical ID(s): {', '.join(missing_ids)}")
    if extra_ids:
        errors.append(f"domains: unexpected ID(s): {', '.join(extra_ids)}")

    return domains_by_id


def _validate_modules(
    modules_value: Any,
    domains_by_id: dict[str, dict[str, Any]],
    last_updated: date | None,
    errors: list[str],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
]:
    modules_by_id: dict[str, dict[str, Any]] = {}
    question_refs: dict[str, list[str]] = {}
    flashcard_refs: dict[str, list[str]] = {}
    lab_refs: dict[str, list[str]] = {}

    if not isinstance(modules_value, list):
        errors.append("modules: expected a list")
        return modules_by_id, question_refs, flashcard_refs, lab_refs
    if len(modules_value) != 24:
        errors.append(f"modules: expected exactly 24 entries, found {len(modules_value)}")

    orders: list[int] = []
    slugs: list[str] = []
    for index, module in enumerate(modules_value):
        context = f"modules[{index}]"
        if not isinstance(module, dict):
            errors.append(f"{context}: expected a mapping")
            continue
        _check_fields(
            module,
            MODULE_REQUIRED_FIELDS,
            MODULE_ALLOWED_FIELDS,
            context,
            errors,
        )

        module_id = module.get("id")
        if not isinstance(module_id, str) or not MODULE_ID_RE.fullmatch(module_id):
            errors.append(f"{context}.id: expected MOD-01 through MOD-24")
            module_key = f"<invalid-{index}>"
        else:
            module_key = module_id
            if module_id in modules_by_id:
                errors.append(f"{context}.id: duplicate module ID {module_id}")
            modules_by_id[module_id] = module

        order = module.get("order")
        if type(order) is not int or not 1 <= order <= 24:
            errors.append(f"{context}.order: expected an integer from 1 through 24")
        else:
            orders.append(order)
            if isinstance(module_id, str) and module_id != f"MOD-{order:02d}":
                errors.append(
                    f"{context}: ID {module_id!r} does not match order {order}"
                )

        domain_id = module.get("domain_id")
        if not isinstance(domain_id, str) or not DOMAIN_ID_RE.fullmatch(domain_id):
            errors.append(
                f"{context}.domain_id: expected DOMAIN-01 through DOMAIN-10"
            )
        elif domain_id not in domains_by_id:
            errors.append(f"{context}.domain_id: unknown domain {domain_id!r}")
        elif (
            isinstance(module_id, str)
            and module_id in EXPECTED_MODULE_DOMAINS
            and domain_id != EXPECTED_MODULE_DOMAINS[module_id]
        ):
            errors.append(
                f"{context}.domain_id: {module_id} belongs to "
                f"{EXPECTED_MODULE_DOMAINS[module_id]}, not {domain_id}"
            )

        slug = module.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
            errors.append(f"{context}.slug: expected a non-empty lowercase kebab-case slug")
        else:
            slugs.append(slug)

        title_el = module.get("title_el")
        if not isinstance(title_el, str) or not title_el.strip():
            errors.append(f"{context}.title_el: expected a non-empty string")
        expected_title = (
            EXPECTED_NEW_MODULE_TITLES.get(module_id)
            if isinstance(module_id, str)
            else None
        )
        if expected_title is not None and title_el != expected_title:
            errors.append(f"{module_id}.title_el: must match the canonical title")

        syllabus_area = module.get("syllabus_area")
        if syllabus_area is not None and (
            not isinstance(syllabus_area, str) or not syllabus_area.strip()
        ):
            errors.append(f"{context}.syllabus_area: expected null or a non-empty string")

        reviewer = module.get("reviewer")
        if reviewer is not None and (
            not isinstance(reviewer, str) or not reviewer.strip()
        ):
            errors.append(f"{context}.reviewer: expected null or a non-empty string")

        status = module.get("status")
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            errors.append(
                f"{context}.status: expected one of {', '.join(sorted(ALLOWED_STATUSES))}"
            )

        available = module.get("available")
        if type(available) is not bool:
            errors.append(f"{context}.available: expected true or false")

        lesson = module.get("lesson")
        lesson_markdown: Path | None = None
        lesson_html: Path | None = None
        if not isinstance(lesson, dict):
            errors.append(f"{context}.lesson: expected a mapping")
        else:
            _check_fields(
                lesson,
                {"markdown", "html"},
                {"markdown", "html"},
                f"{context}.lesson",
                errors,
            )
            lesson_markdown = _safe_file(
                lesson.get("markdown"),
                f"{context}.lesson.markdown",
                errors,
                suffix=".md",
            )
            lesson_html = _safe_file(
                lesson.get("html"),
                f"{context}.lesson.html",
                errors,
                suffix=".html",
            )
        if available is True and (lesson_markdown is None or lesson_html is None):
            errors.append(f"{context}: an available module requires both lesson paths")

        module_questions = _string_list(
            module.get("questions"),
            f"{context}.questions",
            errors,
        )
        module_flashcards = _string_list(
            module.get("flashcards"),
            f"{context}.flashcards",
            errors,
        )
        module_labs = _string_list(module.get("labs"), f"{context}.labs", errors)
        question_refs[module_key] = module_questions
        flashcard_refs[module_key] = module_flashcards
        lab_refs[module_key] = module_labs

        source_references = _string_list(
            module.get("source_references"),
            f"{context}.source_references",
            errors,
        )
        last_verified_value = module.get("last_verified")
        verified_date: date | None = None
        if last_verified_value is not None:
            verified_date = _parse_date(
                last_verified_value,
                f"{context}.last_verified",
                errors,
            )
            if not source_references:
                errors.append(
                    f"{context}: last_verified requires at least one source reference"
                )
            if (
                verified_date is not None
                and last_updated is not None
                and verified_date > last_updated
            ):
                errors.append(f"{context}: last_verified cannot be after last_updated")

        if isinstance(status, str) and status in REVIEWED_STATUSES:
            if not isinstance(syllabus_area, str) or not syllabus_area.strip():
                errors.append(
                    f"{context}: status {status!r} requires syllabus_area"
                )
            if not isinstance(reviewer, str) or not reviewer.strip():
                errors.append(f"{context}: status {status!r} requires reviewer")
            if not source_references:
                errors.append(f"{context}: status {status!r} requires a source reference")
            if last_verified_value is None:
                errors.append(f"{context}: status {status!r} requires last_verified")
            if not module_questions:
                errors.append(f"{context}: status {status!r} requires questions")

    duplicate_orders = sorted(
        str(value) for value, count in Counter(orders).items() if count > 1
    )
    duplicate_slugs = sorted(
        value for value, count in Counter(slugs).items() if count > 1
    )
    if duplicate_orders:
        errors.append(f"modules: duplicate order(s): {', '.join(duplicate_orders)}")
    if duplicate_slugs:
        errors.append(f"modules: duplicate slug(s): {', '.join(duplicate_slugs)}")
    if set(orders) != set(range(1, 25)):
        errors.append("modules: orders must be exactly 1 through 24")

    expected_ids = EXPECTED_MODULE_IDS
    actual_ids = set(modules_by_id)
    missing_ids = sorted(expected_ids - actual_ids)
    extra_ids = sorted(actual_ids - expected_ids)
    if missing_ids:
        errors.append(f"modules: missing canonical ID(s): {', '.join(missing_ids)}")
    if extra_ids:
        errors.append(f"modules: unexpected ID(s): {', '.join(extra_ids)}")

    module_one = modules_by_id.get("MOD-01")
    if module_one is not None:
        if module_one.get("status") != "needs_verification":
            errors.append("MOD-01: status must remain needs_verification")
        if module_one.get("available") is not True:
            errors.append("MOD-01: available must be true")
        if module_one.get("last_verified") is not None:
            errors.append("MOD-01: last_verified must remain null")
        if "reviewer" in module_one:
            errors.append("MOD-01: reviewer must remain absent")
    for number in range(2, 25):
        module_id = f"MOD-{number:02d}"
        module = modules_by_id.get(module_id)
        if module is None:
            continue
        if module.get("available") is not False:
            errors.append(f"{module_id}: available must be false in this pilot")
        if module.get("status") != "planned":
            errors.append(f"{module_id}: status must remain planned in this pilot")
        if "reviewer" in module:
            errors.append(f"{module_id}: planned module must not declare reviewer")

        if number >= 17:
            lesson = module.get("lesson")
            if not isinstance(lesson, dict) or (
                lesson.get("markdown") is not None
                or lesson.get("html") is not None
            ):
                errors.append(f"{module_id}: planned lesson paths must remain null")
            for field in ("questions", "flashcards", "labs", "source_references"):
                if module.get(field) != []:
                    errors.append(f"{module_id}.{field}: planned registry must be empty")
            if module.get("last_verified") is not None:
                errors.append(f"{module_id}: last_verified must remain null")

    return modules_by_id, question_refs, flashcard_refs, lab_refs


def _validate_module_display_codes(
    modules_by_id: dict[str, dict[str, Any]],
    domains_by_id: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    display_code_owners: dict[str, list[str]] = defaultdict(list)
    parsed_codes: dict[str, tuple[int, int]] = {}

    for module_id, module in sorted(modules_by_id.items()):
        context = f"{module_id}.display_code"
        display_code = module.get("display_code")
        if not isinstance(display_code, str):
            errors.append(f"{context}: expected a string")
            continue

        display_code_owners[display_code].append(module_id)
        if not display_code:
            errors.append(f"{context}: expected a non-empty string")
            continue
        if any(character.isspace() for character in display_code):
            errors.append(f"{context}: spaces are not allowed")
        if display_code == module_id:
            errors.append(f"{context}: must not use the technical module ID")

        match = DISPLAY_CODE_RE.fullmatch(display_code)
        if match is None:
            errors.append(
                f"{context}: expected NN.NN with domain 01 through 10 "
                "and a local module number beginning at 01"
            )
        else:
            domain_number = int(match.group("domain"))
            local_number = int(match.group("module"))
            parsed_codes[module_id] = (domain_number, local_number)

            domain_id = module.get("domain_id")
            domain = (
                domains_by_id.get(domain_id)
                if isinstance(domain_id, str)
                else None
            )
            domain_order = domain.get("order") if isinstance(domain, dict) else None
            if type(domain_order) is int and domain_number != domain_order:
                errors.append(
                    f"{context}: domain component {domain_number:02d} does not "
                    f"match {domain_id} order {domain_order:02d}"
                )

        expected_display_code = EXPECTED_MODULE_DISPLAY_CODES.get(module_id)
        if (
            expected_display_code is not None
            and display_code != expected_display_code
        ):
            errors.append(
                f"{context}: expected canonical code {expected_display_code}, "
                f"found {display_code!r}"
            )

    duplicates = sorted(
        (display_code, owners)
        for display_code, owners in display_code_owners.items()
        if len(owners) > 1
    )
    for display_code, owners in duplicates:
        errors.append(
            f"modules: duplicate display_code {display_code!r}: "
            f"{', '.join(owners)}"
        )

    for domain_id, domain in sorted(domains_by_id.items()):
        domain_order = domain.get("order")
        module_ids = domain.get("module_ids")
        if type(domain_order) is not int or not isinstance(module_ids, list):
            continue

        local_numbers: list[int] = []
        sequence_is_complete = True
        for position, module_id in enumerate(module_ids, start=1):
            if not isinstance(module_id, str):
                sequence_is_complete = False
                continue
            parsed_code = parsed_codes.get(module_id)
            if parsed_code is None:
                sequence_is_complete = False
                continue
            domain_number, local_number = parsed_code
            local_numbers.append(local_number)
            if domain_number != domain_order:
                errors.append(
                    f"{module_id}.display_code: domain component "
                    f"{domain_number:02d} does not match registry owner "
                    f"{domain_id} order {domain_order:02d}"
                )
            if local_number != position:
                errors.append(
                    f"{module_id}.display_code: local component "
                    f"{local_number:02d} does not match one-based position "
                    f"{position:02d} in {domain_id}.module_ids"
                )

        if local_numbers and local_numbers[0] != 1:
            errors.append(
                f"{domain_id}: display_code local numbering must begin at 01"
            )
        expected_local_numbers = list(range(1, len(module_ids) + 1))
        if sequence_is_complete and local_numbers != expected_local_numbers:
            errors.append(
                f"{domain_id}: display_code local numbering must be continuous "
                "from 01 in module_ids order"
            )


def _validate_domain_module_relationships(
    domains_by_id: dict[str, dict[str, Any]],
    modules_by_id: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    memberships: dict[str, list[str]] = defaultdict(list)
    for domain_id, domain in domains_by_id.items():
        module_ids = domain.get("module_ids")
        if not isinstance(module_ids, list):
            continue
        for module_id in module_ids:
            if (
                isinstance(module_id, str)
                and domain_id not in memberships[module_id]
            ):
                memberships[module_id].append(domain_id)

    for module_id, owners in sorted(memberships.items()):
        if module_id not in modules_by_id:
            errors.append(
                f"{module_id}: domain registry references a module that is not defined"
            )
        if len(owners) > 1:
            errors.append(
                f"{module_id}: listed in multiple domains: {', '.join(owners)}"
            )

    for module_id, module in sorted(modules_by_id.items()):
        owners = memberships.get(module_id, [])
        if not owners:
            errors.append(f"{module_id}: module is not listed in any domain")
            continue
        if len(owners) != 1:
            continue
        declared_domain = module.get("domain_id")
        if declared_domain != owners[0]:
            errors.append(
                f"{module_id}: domain_id {declared_domain!r} does not agree with "
                f"domain registry owner {owners[0]}"
            )


def _validate_questions(
    value: Any,
    modules_by_id: dict[str, dict[str, Any]],
    module_refs: dict[str, list[str]],
    html_metadata: dict[Path, MetadataParser],
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append("questions: expected a list")
        return

    registry: dict[str, tuple[Path | None, str | None]] = {}
    for index, question in enumerate(value):
        context = f"questions[{index}]"
        if not isinstance(question, dict):
            errors.append(f"{context}: expected a mapping")
            continue
        _check_fields(question, {"id", "html"}, QUESTION_FIELDS, context, errors)

        question_id = question.get("id")
        if not isinstance(question_id, str) or not QUESTION_ID_RE.fullmatch(question_id):
            errors.append(f"{context}.id: invalid question ID")
            continue
        if question_id in registry:
            errors.append(f"{context}.id: duplicate question ID {question_id}")
            continue

        html_path = _safe_file(
            question.get("html"),
            f"{context}.html",
            errors,
            suffix=".html",
        )
        module_id = question.get("module_id")
        if module_id is not None and not isinstance(module_id, str):
            errors.append(f"{context}.module_id: expected a canonical module ID")
            module_id = None
        elif module_id is not None and module_id not in modules_by_id:
            errors.append(f"{context}.module_id: unknown module {module_id!r}")
        registry[question_id] = (html_path, module_id)

    referenced_by: dict[str, list[str]] = defaultdict(list)
    for module_id, references in module_refs.items():
        for question_id in references:
            referenced_by[question_id].append(module_id)
            if question_id not in registry:
                errors.append(
                    f"{module_id}.questions: unregistered question {question_id}"
                )
                continue
            declared_module = registry[question_id][1]
            if declared_module is not None and declared_module != module_id:
                errors.append(
                    f"{question_id}: registry module_id {declared_module} does not "
                    f"match module reference {module_id}"
                )

    for question_id in sorted(registry):
        owners = referenced_by.get(question_id, [])
        if not owners:
            errors.append(f"{question_id}: registry entry is not referenced by a module")
        elif len(owners) > 1:
            errors.append(
                f"{question_id}: referenced by multiple modules: {', '.join(owners)}"
            )

    found: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    for path, metadata in html_metadata.items():
        for question_id, line in metadata.question_ids:
            if not question_id:
                errors.append(
                    f"{_display(path)}:{line}: data-question-id must not be empty"
                )
                continue
            found[question_id].append((path, line))

    for question_id, (declared_html, _) in sorted(registry.items()):
        locations = found.get(question_id, [])
        if len(locations) != 1:
            errors.append(
                f"{question_id}: expected exactly one matching data-question-id, "
                f"found {len(locations)}"
            )
            continue
        actual_html, line = locations[0]
        if declared_html is not None and actual_html != declared_html.resolve():
            errors.append(
                f"{_display(actual_html)}:{line}: {question_id} is registered for "
                f"{_display(declared_html.resolve())}"
            )

    for question_id, locations in sorted(found.items()):
        if question_id not in registry:
            location_text = ", ".join(
                f"{_display(path)}:{line}" for path, line in locations
            )
            errors.append(
                f"unregistered data-question-id {question_id!r} at {location_text}"
            )


def _validate_flashcards(
    value: Any,
    modules_by_id: dict[str, dict[str, Any]],
    module_refs: dict[str, list[str]],
    html_metadata: dict[Path, MetadataParser],
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append("flashcards: expected a list")
        return

    registry: dict[str, tuple[Path | None, str | None]] = {}
    for index, flashcard in enumerate(value):
        context = f"flashcards[{index}]"
        if not isinstance(flashcard, dict):
            errors.append(f"{context}: expected a mapping")
            continue
        _check_fields(
            flashcard,
            FLASHCARD_REQUIRED_FIELDS,
            FLASHCARD_FIELDS,
            context,
            errors,
        )

        flashcard_id = flashcard.get("id")
        if (
            not isinstance(flashcard_id, str)
            or not FLASHCARD_ID_RE.fullmatch(flashcard_id)
        ):
            errors.append(f"{context}.id: invalid flashcard ID")
            continue
        if flashcard_id in registry:
            errors.append(f"{context}.id: duplicate flashcard ID {flashcard_id}")
            continue

        html_path = _safe_file(
            flashcard.get("html"),
            f"{context}.html",
            errors,
            suffix=".html",
        )
        if html_path is None:
            errors.append(f"{context}.html: a flashcard requires a valid HTML file")

        if "markdown" in flashcard:
            markdown_path = _safe_file(
                flashcard.get("markdown"),
                f"{context}.markdown",
                errors,
                suffix=".md",
            )
            if markdown_path is None:
                errors.append(
                    f"{context}.markdown: expected a valid Markdown file when present"
                )

        module_id = flashcard.get("module_id")
        if not isinstance(module_id, str):
            errors.append(f"{context}.module_id: expected a canonical module ID")
            module_id = None
        elif module_id not in modules_by_id:
            errors.append(f"{context}.module_id: unknown module {module_id!r}")
        registry[flashcard_id] = (html_path, module_id)

    referenced_by: dict[str, list[str]] = defaultdict(list)
    for module_id, references in module_refs.items():
        for flashcard_id in references:
            referenced_by[flashcard_id].append(module_id)
            if flashcard_id not in registry:
                errors.append(
                    f"{module_id}.flashcards: unregistered flashcard {flashcard_id}"
                )
                continue
            declared_module = registry[flashcard_id][1]
            if declared_module is not None and declared_module != module_id:
                errors.append(
                    f"{flashcard_id}: registry module_id {declared_module} does not "
                    f"match module reference {module_id}"
                )

    for flashcard_id in sorted(registry):
        owners = referenced_by.get(flashcard_id, [])
        if not owners:
            errors.append(
                f"{flashcard_id}: registry entry is not referenced by a module"
            )
        elif len(owners) > 1:
            errors.append(
                f"{flashcard_id}: referenced by multiple modules: "
                f"{', '.join(owners)}"
            )

    found: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    for path, metadata in html_metadata.items():
        for flashcard_id, line in metadata.flashcard_ids:
            if not flashcard_id:
                errors.append(
                    f"{_display(path)}:{line}: data-flashcard-id must not be empty"
                )
                continue
            found[flashcard_id].append((path, line))

    for flashcard_id, (declared_html, _) in sorted(registry.items()):
        locations = found.get(flashcard_id, [])
        if len(locations) != 1:
            errors.append(
                f"{flashcard_id}: expected exactly one matching data-flashcard-id, "
                f"found {len(locations)}"
            )
            continue
        actual_html, line = locations[0]
        if declared_html is not None and actual_html != declared_html.resolve():
            errors.append(
                f"{_display(actual_html)}:{line}: {flashcard_id} is registered for "
                f"{_display(declared_html.resolve())}"
            )

    for flashcard_id, locations in sorted(found.items()):
        if flashcard_id not in registry:
            location_text = ", ".join(
                f"{_display(path)}:{line}" for path, line in locations
            )
            errors.append(
                f"unregistered data-flashcard-id {flashcard_id!r} at {location_text}"
            )


def _validate_labs(
    value: Any,
    modules_by_id: dict[str, dict[str, Any]],
    module_refs: dict[str, list[str]],
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append("labs: expected a list")
        return

    registry: dict[str, str | None] = {}
    for index, lab in enumerate(value):
        context = f"labs[{index}]"
        if not isinstance(lab, dict):
            errors.append(f"{context}: expected a mapping")
            continue
        _check_fields(lab, {"id", "markdown", "html"}, LAB_FIELDS, context, errors)

        lab_id = lab.get("id")
        if not isinstance(lab_id, str) or not LAB_ID_RE.fullmatch(lab_id):
            errors.append(f"{context}.id: invalid lab ID")
            continue
        if lab_id in registry:
            errors.append(f"{context}.id: duplicate lab ID {lab_id}")
            continue

        _safe_file(lab.get("markdown"), f"{context}.markdown", errors, suffix=".md")
        _safe_file(lab.get("html"), f"{context}.html", errors, suffix=".html")
        module_id = lab.get("module_id")
        if module_id is not None and not isinstance(module_id, str):
            errors.append(f"{context}.module_id: expected a canonical module ID")
            module_id = None
        elif module_id is not None and module_id not in modules_by_id:
            errors.append(f"{context}.module_id: unknown module {module_id!r}")
        registry[lab_id] = module_id

    referenced_by: dict[str, list[str]] = defaultdict(list)
    for module_id, references in module_refs.items():
        for lab_id in references:
            referenced_by[lab_id].append(module_id)
            if lab_id not in registry:
                errors.append(f"{module_id}.labs: unregistered lab {lab_id}")
                continue
            declared_module = registry[lab_id]
            if declared_module is not None and declared_module != module_id:
                errors.append(
                    f"{lab_id}: registry module_id {declared_module} does not "
                    f"match module reference {module_id}"
                )

    for lab_id in sorted(registry):
        owners = referenced_by.get(lab_id, [])
        if not owners:
            errors.append(f"{lab_id}: registry entry is not referenced by a module")
        elif len(owners) > 1:
            errors.append(f"{lab_id}: referenced by multiple modules: {', '.join(owners)}")


def _validate_render_hosts(
    html_metadata: dict[Path, MetadataParser],
    errors: list[str],
) -> None:
    expectations = (
        ("curriculum.html", "data-domain-navigation"),
        ("curriculum.html", "data-curriculum-domains"),
        ("index.html", "data-home-domains"),
    )
    for relative_path, attribute in expectations:
        path = (ROOT / relative_path).resolve()
        metadata = html_metadata.get(path)
        if metadata is None:
            errors.append(f"{relative_path}: cannot inspect dynamic render hosts")
            continue
        lines = metadata.render_hosts.get(attribute, [])
        if len(lines) != 1:
            errors.append(
                f"{relative_path}: expected exactly one [{attribute}] render host, "
                f"found {len(lines)}"
            )


def _validate_generated_data(data: Any, errors: list[str]) -> None:
    try:
        expected = render_curriculum_data(data)
    except ValueError as exc:
        errors.append(f"generated curriculum projection: {exc}")
        return
    try:
        current = GENERATED_DATA.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(
            "assets/curriculum-data.js: missing; run "
            "'python scripts/generate_curriculum_data.py'"
        )
        return
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"assets/curriculum-data.js: cannot read valid UTF-8: {exc}")
        return
    if current != expected:
        errors.append(
            "assets/curriculum-data.js is stale; run "
            "'python scripts/generate_curriculum_data.py'"
        )


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"required file is missing: {relative}")

    try:
        data = load(CURRICULUM)
    except (OSError, CurriculumYAMLError) as exc:
        errors.append(f"cannot parse data/curriculum.yml: {exc}")
        data = None

    if not isinstance(data, dict):
        if data is not None:
            errors.append("curriculum root must be a mapping")
    else:
        _check_fields(data, TOP_LEVEL_FIELDS, TOP_LEVEL_FIELDS, "curriculum", errors)
        if data.get("version") != 1 or type(data.get("version")) is not int:
            errors.append("version: expected integer 1")
        last_updated = _parse_date(data.get("last_updated"), "last_updated", errors)
        html_metadata = _load_html_metadata(errors)
        domains_by_id = _validate_domains(data.get("domains"), errors)
        modules_by_id, question_refs, flashcard_refs, lab_refs = _validate_modules(
            data.get("modules"),
            domains_by_id,
            last_updated,
            errors,
        )
        _validate_module_display_codes(
            modules_by_id,
            domains_by_id,
            errors,
        )
        _validate_domain_module_relationships(
            domains_by_id,
            modules_by_id,
            errors,
        )
        _validate_questions(
            data.get("questions"),
            modules_by_id,
            question_refs,
            html_metadata,
            errors,
        )
        _validate_flashcards(
            data.get("flashcards"),
            modules_by_id,
            flashcard_refs,
            html_metadata,
            errors,
        )
        _validate_labs(
            data.get("labs"),
            modules_by_id,
            lab_refs,
            errors,
        )
        _validate_render_hosts(html_metadata, errors)
        _validate_generated_data(data, errors)

    if errors:
        print(
            f"Curriculum validation failed with {len(errors)} error(s):",
            file=sys.stderr,
        )
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Curriculum validation passed: 10 domains, 24 canonical modules "
        "and references are valid."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
