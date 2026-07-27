#!/usr/bin/env python3
"""Generate the readable report for the canonical theory coverage map."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from curriculum_yaml import CurriculumYAMLError, load
from validate_theory_coverage import (
    COVERAGE_PATH,
    CURRICULUM_PATH,
    ROOT,
    build_coverage_audit,
    validate_theory_coverage,
)


OUTPUT = ROOT / "docs" / "THEORY_COVERAGE_MAP.md"
HEADER = (
    "<!-- Generated from data/theory-coverage.yml by "
    "scripts/generate_theory_coverage_report.py. Do not edit directly. -->\n"
)


def _markdown(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _references_text(references: list[dict[str, Any]]) -> str:
    values: list[str] = []
    for reference in references:
        role = reference["role"]
        pages = reference["pages"]
        values.append(pages if role == "question" else f"{role}: {pages}")
    return ", ".join(values)


def render_theory_coverage_report(
    coverage: dict[str, Any], curriculum: dict[str, Any]
) -> str:
    """Return the deterministic Markdown report for validated parsed data."""

    errors = validate_theory_coverage(coverage, curriculum)
    if errors:
        rendered_errors = "\n".join(f"- {error}" for error in errors)
        raise ValueError(
            "cannot generate a report from invalid theory coverage data:\n"
            f"{rendered_errors}"
        )

    audit = build_coverage_audit(coverage, curriculum)
    source = coverage["source"]
    domains = curriculum["domains"]
    modules = curriculum["modules"]
    chapters = coverage["chapters"]
    questions = coverage["questions"]
    module_by_id = {module["id"]: module for module in modules}
    chapters_by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chapter in chapters:
        chapters_by_module[chapter["module_id"]].append(chapter)
    for module_chapters in chapters_by_module.values():
        module_chapters.sort(key=lambda chapter: chapter["code"])
    question_by_id = {question["id"]: question for question in questions}

    lines = [
        HEADER.rstrip("\n"),
        "",
        "# Theory Coverage Map",
        "",
        "## Σκοπός και όρια",
        "",
        (
            "Ο χάρτης αποτυπώνει τον σχεδιασμό κάλυψης των 318 θεωρητικών "
            "ερωτήσεων της μοναδικής πηγής γνώσης του έργου. Συνδέει κάθε "
            "ταυτότητα ερώτησης με έναν υπάρχοντα θεματικό τομέα, μία μόνιμη "
            "τεχνική ταυτότητα module και ένα μελλοντικό κεφάλαιο θεωρίας."
        ),
        "",
        (
            "Η ταξινομία κεφαλαίων είναι παιδαγωγική δομή της εφαρμογής και "
            "δεν αποτελεί διαίρεση ή αρίθμηση που δηλώνεται από το PDF. Η "
            "παρούσα εργασία δεν προσθέτει πλήρη θεωρία ή διαδραστικό "
            "εκπαιδευτικό υλικό. Όλες οι αντιστοιχίσεις και όλα τα κεφάλαια "
            "παραμένουν `needs_verification` μέχρι μεταγενέστερο ανθρώπινο έλεγχο."
        ),
        "",
        f"Μοναδική πηγή γνώσης: [{source['id']}]({source['url']}).",
        "",
        (
            "Όλες οι σελίδες έχουν αρίθμηση από το 1 "
            "(`pdf_viewer_1_based`): η "
            "πρώτη σελίδα που εμφανίζει ένας συνήθης PDF viewer είναι η "
            "σελίδα 1. Οι εσωτερικοί τυπωμένοι αριθμοί σελίδων δεν "
            "χρησιμοποιούνται ως κανονικές αναφορές."
        ),
        "",
        "## Αναγνωριστικά",
        "",
        "- `A-NNN` / `B-NNN`: σταθερή ταυτότητα ερώτησης πηγής.",
        "- `DOMAIN-NN`: τεχνική ταυτότητα θεματικού τομέα.",
        "- `MOD-NN`: μόνιμη τεχνική ταυτότητα module.",
        "- `NN.NN`: κωδικός module που βλέπει ο εκπαιδευόμενος.",
        "- `NN.NN.NN`: κωδικός μελλοντικού κεφαλαίου θεωρίας.",
        "- `CH-NN-NN-NN`: τεχνική ταυτότητα μελλοντικού κεφαλαίου.",
        "",
        (
            "Η αρίθμηση κεφαλαίων δεν είναι αρίθμηση ερωτήσεων του PDF. "
            "Παράδειγμα: `02.02 / MOD-17` περιέχει κεφάλαια όπως "
            "`02.02.01 / CH-02-02-01`."
        ),
        "",
        "## Επαλήθευση corpus",
        "",
        "| Ομάδα | Πρώτη ταυτότητα | Τελευταία ταυτότητα | Ερωτήσεις | Σελίδες ενότητας |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for group in ("A", "B"):
        metadata = source["question_groups"][group]
        lines.append(
            f"| {group} | `{metadata['first_id']}` | `{metadata['last_id']}` | "
            f"{metadata['count']} | {metadata['source_pages']} |"
        )
    if 50 <= audit["total_chapter_count"] <= 80:
        chapter_count_rationale = (
            f"Τα {audit['total_chapter_count']} κεφάλαια βρίσκονται μέσα "
            "στον ενδεικτικό στόχο 50–80. Συγχωνεύουν επικαλυπτόμενα θέματα "
            "των δύο ομάδων μέσα στο ίδιο module, αλλά διατηρούν χωριστούς "
            "μαθησιακούς στόχους· δεν δημιουργούνται κενά κεφάλαια για "
            "modules χωρίς κάλυψη."
        )
    else:
        chapter_count_rationale = (
            f"Τα {audit['total_chapter_count']} κεφάλαια προκύπτουν από "
            "συνεκτικούς μαθησιακούς στόχους και όχι από αριθμητική ποσόστωση. "
            "Δεν δημιουργούνται κενά κεφάλαια για modules χωρίς κάλυψη."
        )

    lines.extend(
        [
            "",
            (
                f"Το PDF έχει {source['page_count']} σελίδες viewer. Η Ομάδα Α "
                "αρχίζει στη σελίδα 2 και η αριθμημένη ερώτηση 89 εμφανίζεται "
                "στη σελίδα 35· η απάντησή της συνεχίζεται στη σελίδα 36. Η "
                "Ομάδα Β καλύπτει τις σελίδες 37–150. Η σελίδα 151 αρχίζει το "
                "πρακτικό μέρος και δεν ανήκει στο θεωρητικό corpus."
            ),
            "",
            (
                "Η αντιστοίχιση ταυτοτήτων είναι άμεση ανά ομάδα: ο αριθμός "
                "`n` της Ομάδας Α γίνεται `A-nnn` και ο αριθμός `n` της "
                "Ομάδας Β γίνεται `B-nnn`, με συμπλήρωση τριών ψηφίων. "
                "Δεν εντοπίστηκαν ελλείψεις, διπλότυπα ή αμφίσημοι αριθμοί."
            ),
            "",
            "## Συνολικός έλεγχος κάλυψης",
            "",
            f"- Ομάδα Α: {audit['group_counts']['A']} ερωτήσεις",
            f"- Ομάδα Β: {audit['group_counts']['B']} ερωτήσεις",
            f"- Σύνολο: {audit['total_question_count']} ερωτήσεις",
            f"- Μελλοντικά κεφάλαια: {audit['total_chapter_count']}",
            f"- Modules με κάλυψη: {len(audit['covered_modules'])}",
            f"- Modules χωρίς κάλυψη: {len(audit['zero_coverage_modules'])}",
            (
                "- Κατάσταση ερωτήσεων: "
                f"`needs_verification` {audit['question_statuses']['needs_verification']}, "
                f"`verified` {audit['question_statuses']['verified']}"
            ),
            (
                "- Κατάσταση κεφαλαίων: "
                f"`needs_verification` {audit['chapter_statuses']['needs_verification']}, "
                f"`verified` {audit['chapter_statuses']['verified']}"
            ),
            f"- Ερωτήσεις με συγκεκριμένη σημείωση αμφισημίας: {len(audit['ambiguity_question_ids'])}",
            (
                "- Εύρος σελίδων αριθμημένων θεωρητικών ερωτήσεων: "
                f"{audit['source_page_minimum']}–{audit['source_page_maximum']}"
            ),
            "",
            chapter_count_rationale,
            "",
            "## Κάλυψη ανά θεματικό τομέα",
            "",
            "| Τομέας | Τίτλος | Ερωτήσεις | Κεφάλαια |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for domain in domains:
        domain_id = domain["id"]
        lines.append(
            f"| `{domain_id}` | {_markdown(domain['title'])} | "
            f"{audit['question_count_by_domain'][domain_id]} | "
            f"{audit['chapter_count_by_domain'][domain_id]} |"
        )

    lines.extend(
        [
            "",
            "## Κάλυψη ανά module",
            "",
            "| Module | Τίτλος | Τομέας | Ερωτήσεις | Κεφάλαια | Κάλυψη |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for module in modules:
        module_id = module["id"]
        question_count = audit["question_count_by_module"][module_id]
        chapter_count = audit["chapter_count_by_module"][module_id]
        coverage_label = "mapped" if question_count else "coverage_gap"
        lines.append(
            f"| `{module['display_code']} / {module_id}` | "
            f"{_markdown(module['title_el'])} | `{module['domain_id']}` | "
            f"{question_count} | {chapter_count} | `{coverage_label}` |"
        )

    lines.extend(
        [
            "",
            "## Modules χωρίς αντιστοιχισμένες ερωτήσεις",
            "",
        ]
    )
    if audit["zero_coverage_modules"]:
        for module_id in audit["zero_coverage_modules"]:
            module = module_by_id[module_id]
            lines.append(
                f"- `{module['display_code']} / {module_id}` — "
                f"{module['title_el']}: δεν έχει αντιστοιχισμένη ερώτηση. "
                "Καταγράφεται ως κενό μεταξύ του corpus και της ευρύτερης "
                "ταξινομίας της εφαρμογής· χρειάζεται ανθρώπινος έλεγχος για "
                "να διακριθεί περιορισμός της πηγής από πιθανό θέμα ταξινόμησης."
            )
    else:
        lines.append("- Κανένα.")

    lines.extend(["", "## Διάρθρωση μελλοντικών κεφαλαίων", ""])
    for domain in domains:
        domain_modules = [
            module
            for module in modules
            if module["domain_id"] == domain["id"]
            and chapters_by_module[module["id"]]
        ]
        if not domain_modules:
            continue
        lines.extend(
            [
                f"### `{domain['id']}` — {domain['title']}",
                "",
            ]
        )
        for module in domain_modules:
            module_chapters = chapters_by_module[module["id"]]
            lines.extend(
                [
                    f"#### `{module['display_code']} / {module['id']}` — {module['title_el']}",
                    "",
                ]
            )
            for chapter in module_chapters:
                lines.append(
                    f"- `{chapter['code']} / {chapter['id']}` — "
                    f"**{chapter['title_el']}** · "
                    f"{len(chapter['question_ids'])} ερωτήσεις · "
                    f"σελίδες {_references_text(chapter['source_references'])} · "
                    f"`{chapter['status']}`"
                )
                lines.append(f"  {chapter['summary_el']}")
            lines.append("")

    lines.extend(
        [
            "## Αμφισημίες που καταγράφονται",
            "",
        ]
    )
    if audit["ambiguity_question_ids"]:
        for question_id in audit["ambiguity_question_ids"]:
            question = question_by_id[question_id]
            lines.append(
                f"- `{question_id}` (`{question['chapter_id']}`, σελίδα "
                f"{_references_text(question['source_references'])}): "
                f"{question['notes']}"
            )
    else:
        lines.append(
            "- Δεν καταγράφηκε ειδική αμφισημία πέρα από την καθολική ανάγκη "
            "ανθρώπινης επαλήθευσης."
        )

    lines.extend(
        [
            "",
            "## Ιχνηλασιμότητα και επόμενος έλεγχος",
            "",
            (
                "Η κανονική αλυσίδα είναι: PDF viewer page → source-question "
                "ID → future theory chapter → permanent module ID / learner "
                "module code → domain ID. Η αντίστροφη διαδρομή προκύπτει από "
                "τα `question_ids` κάθε κεφαλαίου και τα `source_references` "
                "κάθε ερώτησης."
            ),
            "",
            (
                f"Και οι {audit['total_question_count']} αντιστοιχίσεις και τα "
                f"{audit['total_chapter_count']} κεφάλαια χρειάζονται "
                "μεταγενέστερο ανθρώπινο έλεγχο. Η πηγή αλήθειας για τους "
                "παρόντες αριθμούς είναι αποκλειστικά το "
                "`data/theory-coverage.yml`· το παρόν αρχείο είναι παραγόμενο."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when docs/THEORY_COVERAGE_MAP.md is stale",
    )
    args = parser.parse_args(argv)

    try:
        coverage = load(COVERAGE_PATH)
        curriculum = load(CURRICULUM_PATH)
        expected = render_theory_coverage_report(coverage, curriculum)
    except (OSError, CurriculumYAMLError, ValueError) as exc:
        print(f"Theory coverage report generation failed: {exc}", file=sys.stderr)
        return 1

    if args.check:
        try:
            current = OUTPUT.read_text(encoding="utf-8")
        except FileNotFoundError:
            current = None
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Cannot read {OUTPUT.relative_to(ROOT)}: {exc}", file=sys.stderr)
            return 1
        if current != expected:
            print(
                "docs/THEORY_COVERAGE_MAP.md is stale; run "
                "'python scripts/generate_theory_coverage_report.py'.",
                file=sys.stderr,
            )
            return 1
        print("Generated theory coverage report is in sync.")
        return 0

    try:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(expected)
    except OSError as exc:
        print(f"Cannot write {OUTPUT.relative_to(ROOT)}: {exc}", file=sys.stderr)
        return 1

    print(f"Generated {OUTPUT.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
