#!/usr/bin/env python3
"""Regression tests for the canonical theory coverage map."""

from __future__ import annotations

import unittest
from copy import deepcopy

from curriculum_yaml import load
from generate_theory_coverage_report import (
    OUTPUT,
    render_theory_coverage_report,
)
from validate_theory_coverage import (
    COVERAGE_PATH,
    CURRICULUM_PATH,
    build_coverage_audit,
    validate_theory_coverage,
)


class TheoryCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.coverage = load(COVERAGE_PATH)
        cls.curriculum = load(CURRICULUM_PATH)

    def errors(self, coverage: dict) -> list[str]:
        return validate_theory_coverage(coverage, self.curriculum)

    def assert_rejected(self, coverage: dict, expected: str) -> None:
        errors = self.errors(coverage)
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected an error containing {expected!r}; got:\n"
            + "\n".join(errors),
        )

    @staticmethod
    def question(coverage: dict, question_id: str) -> dict:
        return next(
            question
            for question in coverage["questions"]
            if question["id"] == question_id
        )

    @staticmethod
    def chapter(coverage: dict, chapter_id: str) -> dict:
        return next(
            chapter
            for chapter in coverage["chapters"]
            if chapter["id"] == chapter_id
        )

    @staticmethod
    def module_with_chapters(coverage: dict, minimum: int = 1) -> tuple[str, list[dict]]:
        module_ids = dict.fromkeys(
            chapter["module_id"] for chapter in coverage["chapters"]
        )
        for module_id in module_ids:
            chapters = [
                chapter
                for chapter in coverage["chapters"]
                if chapter["module_id"] == module_id
            ]
            if len(chapters) >= minimum:
                return module_id, chapters
        raise AssertionError(f"no module has at least {minimum} chapters")

    def test_canonical_dataset_passes(self) -> None:
        self.assertEqual(self.errors(self.coverage), [])

    def test_exact_total_question_count(self) -> None:
        audit = build_coverage_audit(self.coverage, self.curriculum)
        self.assertEqual(audit["total_question_count"], 318)

    def test_exact_group_a_count(self) -> None:
        audit = build_coverage_audit(self.coverage, self.curriculum)
        self.assertEqual(audit["group_counts"]["A"], 89)

    def test_exact_group_b_count(self) -> None:
        audit = build_coverage_audit(self.coverage, self.curriculum)
        self.assertEqual(audit["group_counts"]["B"], 229)

    def test_missing_question_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"] = coverage["questions"][:-1]
        self.assert_rejected(coverage, "missing expected question ID")

    def test_duplicate_question_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"].append(deepcopy(coverage["questions"][0]))
        self.assert_rejected(coverage, "duplicate question ID")

    def test_unexpected_question_id_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        extra = deepcopy(coverage["questions"][-1])
        extra["id"] = "B-230"
        extra["number"] = 230
        coverage["questions"].append(extra)
        self.chapter(coverage, extra["chapter_id"])["question_ids"].append("B-230")
        self.assert_rejected(coverage, "unexpected question ID")

    def test_incorrect_group_a_range_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["source"]["question_groups"]["A"]["first_id"] = "A-002"
        self.assert_rejected(coverage, "question_groups.A.first_id")

    def test_incorrect_group_b_range_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["source"]["question_groups"]["B"]["last_id"] = "B-228"
        self.assert_rejected(coverage, "question_groups.B.last_id")

    def test_id_group_mismatch_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["group"] = "B"
        self.assert_rejected(coverage, "ID/group mismatch")

    def test_id_number_mismatch_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["number"] = 2
        self.assert_rejected(coverage, "ID/number mismatch")

    def test_invalid_domain_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["domain_id"] = "DOMAIN-99"
        self.assert_rejected(coverage, "references an unknown domain")

    def test_invalid_module_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["module_id"] = "MOD-99"
        self.assert_rejected(coverage, "references an unknown module")

    def test_module_domain_ownership_mismatch_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        question = coverage["questions"][0]
        question["domain_id"] = next(
            domain["id"]
            for domain in self.curriculum["domains"]
            if domain["id"] != question["domain_id"]
        )
        self.assert_rejected(coverage, "module/domain ownership mismatch")

    def test_chapter_module_domain_ownership_mismatch_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        chapter = coverage["chapters"][0]
        chapter["domain_id"] = next(
            domain["id"]
            for domain in self.curriculum["domains"]
            if domain["id"] != chapter["domain_id"]
        )
        self.assert_rejected(coverage, "module/domain ownership mismatch")

    def test_question_chapter_ownership_mismatch_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        question = coverage["questions"][0]
        question["chapter_id"] = next(
            chapter["id"]
            for chapter in coverage["chapters"]
            if chapter["module_id"] != question["module_id"]
        )
        self.assert_rejected(coverage, "question/chapter ownership mismatch")

    def test_missing_chapter_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["chapter_id"] = "CH-99-99-99"
        self.assert_rejected(coverage, "references a missing chapter")

    def test_wrong_chapter_prefix_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][0]["code"] = "99.99.01"
        self.assert_rejected(coverage, "chapter code prefix")

    def test_chapter_id_code_mismatch_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][0]["code"] = "01.01.99"
        self.assert_rejected(coverage, "chapter ID/code mismatch")

    def test_duplicate_chapter_code_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][1]["code"] = coverage["chapters"][0]["code"]
        self.assert_rejected(coverage, "duplicate chapter code")

    def test_duplicate_chapter_id_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][1]["id"] = coverage["chapters"][0]["id"]
        self.assert_rejected(coverage, "duplicate chapter ID")

    def test_chapter_numbering_gap_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        _module_id, chapters = self.module_with_chapters(coverage, minimum=2)
        last = chapters[-1]
        parts = last["code"].split(".")
        parts[-1] = f"{int(parts[-1]) + 1:02d}"
        last["code"] = ".".join(parts)
        self.assert_rejected(coverage, "chapter numbering must be continuous")

    def test_chapter_numbering_not_beginning_at_one_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        _module_id, chapters = self.module_with_chapters(coverage)
        for chapter in chapters:
            parts = chapter["code"].split(".")
            parts[-1] = f"{int(parts[-1]) + 1:02d}"
            chapter["code"] = ".".join(parts)
        self.assert_rejected(coverage, "chapter numbering must begin at 01")

    def test_orphaned_question_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        question = coverage["questions"][0]
        chapter = self.chapter(coverage, question["chapter_id"])
        chapter["question_ids"].remove(question["id"])
        self.assert_rejected(coverage, "orphaned question")

    def test_empty_chapter_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][0]["question_ids"] = []
        self.assert_rejected(coverage, "question_ids must be a non-empty list")

    def test_non_reciprocal_relationship_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        _module_id, chapters = self.module_with_chapters(coverage, minimum=2)
        question_id = chapters[0]["question_ids"][0]
        self.question(coverage, question_id)["chapter_id"] = chapters[1]["id"]
        self.assert_rejected(coverage, "non-reciprocal")

    def test_question_listed_by_multiple_chapters_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        _module_id, chapters = self.module_with_chapters(coverage, minimum=2)
        question_id = chapters[0]["question_ids"][0]
        chapters[1]["question_ids"].append(question_id)
        self.assert_rejected(coverage, "listed by multiple chapters")

    def test_duplicate_question_inside_chapter_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        chapter = coverage["chapters"][0]
        chapter["question_ids"].append(chapter["question_ids"][0])
        self.assert_rejected(coverage, "contains a duplicate question")

    def test_missing_source_reference_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"] = []
        self.assert_rejected(coverage, "source_references must be a non-empty list")

    def test_chapter_missing_source_reference_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][0]["source_references"] = []
        self.assert_rejected(coverage, "source_references must be a non-empty list")

    def test_missing_question_role_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["role"] = "answer"
        self.assert_rejected(coverage, "must include role 'question'")

    def test_unsupported_reference_role_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["role"] = "citation"
        self.assert_rejected(coverage, ".role must be one of")

    def test_malformed_page_reference_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["pages"] = "2,3"
        self.assert_rejected(coverage, "malformed page reference")

    def test_non_string_page_reference_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["pages"] = 2
        self.assert_rejected(coverage, ".pages must be a string")

    def test_zero_based_page_reference_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["pages"] = "0"
        self.assert_rejected(coverage, "zero-based page reference")

    def test_page_above_pdf_count_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["pages"] = "152"
        self.assert_rejected(coverage, "exceeds PDF viewer page count")

    def test_extremely_large_page_range_is_rejected_without_expansion(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0][
            "pages"
        ] = "1-999999999999999999999999999999"
        self.assert_rejected(coverage, "exceeds PDF viewer page count")

    def test_overlong_page_integer_is_rejected_without_conversion_crash(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0][
            "pages"
        ] = "1" + ("0" * 5000)
        self.assert_rejected(coverage, "exceeds PDF viewer page count")

    def test_question_page_outside_group_range_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        self.question(coverage, "A-001")["source_references"][0][
            "pages"
        ] = "150"
        self.assert_rejected(coverage, "outside its verified viewer-page range")

    def test_audited_question_page_map_is_enforced(self) -> None:
        coverage = deepcopy(self.coverage)
        self.question(coverage, "A-001")["source_references"][0]["pages"] = "3"
        self.assert_rejected(coverage, "does not match the audited PDF corpus")

    def test_question_reference_must_identify_one_page(self) -> None:
        coverage = deepcopy(self.coverage)
        self.question(coverage, "A-001")["source_references"][0][
            "pages"
        ] = "2-3"
        self.assert_rejected(coverage, "exactly one numbered-question viewer page")

    def test_question_pages_must_be_non_decreasing(self) -> None:
        coverage = deepcopy(self.coverage)
        self.question(coverage, "A-001")["source_references"][0]["pages"] = "3"
        self.question(coverage, "A-002")["source_references"][0]["pages"] = "2"
        self.assert_rejected(coverage, "pages must be non-decreasing")

    def test_reversed_page_range_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["pages"] = "3-2"
        self.assert_rejected(coverage, "reversed page range")

    def test_unhashable_scalar_values_are_rejected_without_crashing(self) -> None:
        cases = [
            (
                lambda coverage: coverage["questions"][0].__setitem__(
                    "group", []
                ),
                ".group must be A or B",
            ),
            (
                lambda coverage: coverage["questions"][0].__setitem__(
                    "domain_id", []
                ),
                "references an unknown domain",
            ),
            (
                lambda coverage: coverage["questions"][0].__setitem__(
                    "module_id", {}
                ),
                "references an unknown module",
            ),
            (
                lambda coverage: coverage["questions"][0][
                    "source_references"
                ][0].__setitem__("role", []),
                ".role must be one of",
            ),
            (
                lambda coverage: coverage["chapters"][0].__setitem__(
                    "status", {}
                ),
                "unsupported status",
            ),
        ]
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                coverage = deepcopy(self.coverage)
                mutate(coverage)
                self.assert_rejected(coverage, expected)

    def test_unknown_source_id_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["source_references"][0]["source_id"] = "OTHER"
        self.assert_rejected(coverage, "must be the sole source")

    def test_unsupported_status_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["mapping_status"] = "draft"
        self.assert_rejected(coverage, "unsupported status")

    def test_verified_question_mapping_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["mapping_status"] = "verified"
        self.assert_rejected(coverage, "verified question mapping is not allowed")

    def test_verified_chapter_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][0]["status"] = "verified"
        self.assert_rejected(coverage, "verified chapter is not allowed")

    def test_invalid_topic_without_greek_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["topic_el"] = "ASCII only"
        self.assert_rejected(coverage, "must contain Greek text")

    def test_short_fake_topic_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["topic_el"] = "x α"
        self.assert_rejected(coverage, "meaningful concise Greek description")

    def test_multiline_topic_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["topic_el"] = "Έννοια\nδικτύου"
        self.assert_rejected(coverage, "single-line topic description")

    def test_overlong_topic_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["topic_el"] = "Ε" * 121
        self.assert_rejected(coverage, "no longer than 120 characters")

    def test_invalid_notes_type_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["questions"][0]["notes"] = []
        self.assert_rejected(coverage, "notes must be null or a string")

    def test_chapter_reference_union_is_enforced(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["chapters"][0]["source_references"][0]["pages"] = "151"
        self.assert_rejected(coverage, "assigned-question page union")

    def test_zero_coverage_module_is_reported_without_chapter(self) -> None:
        audit = build_coverage_audit(self.coverage, self.curriculum)
        chapter_modules = {
            chapter["module_id"] for chapter in self.coverage["chapters"]
        }
        for module_id in audit["zero_coverage_modules"]:
            self.assertNotIn(module_id, chapter_modules)
        self.assertEqual(
            len(audit["covered_modules"]) + len(audit["zero_coverage_modules"]),
            24,
        )

    def test_artificial_chapter_for_zero_coverage_module_is_rejected(self) -> None:
        coverage = deepcopy(self.coverage)
        audit = build_coverage_audit(coverage, self.curriculum)
        self.assertTrue(audit["zero_coverage_modules"])
        zero_module_id = audit["zero_coverage_modules"][0]
        zero_module = next(
            module
            for module in self.curriculum["modules"]
            if module["id"] == zero_module_id
        )
        copied = deepcopy(coverage["chapters"][0])
        copied["id"] = f"CH-{zero_module['display_code'].replace('.', '-')}-01"
        copied["code"] = f"{zero_module['display_code']}.01"
        copied["domain_id"] = zero_module["domain_id"]
        copied["module_id"] = zero_module_id
        coverage["chapters"].append(copied)
        self.assert_rejected(
            coverage, "zero-coverage module must not have artificial chapters"
        )

    def test_source_metadata_id_is_enforced(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["source"]["id"] = "OTHER"
        self.assert_rejected(coverage, "source.id must be")

    def test_source_metadata_url_is_enforced(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["source"]["url"] = "https://example.invalid/source.pdf"
        self.assert_rejected(coverage, "source.url must match")

    def test_source_page_numbering_is_enforced(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["source"]["page_numbering"] = "printed"
        self.assert_rejected(coverage, "source.page_numbering must be")

    def test_source_page_count_is_enforced(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["source"]["page_count"] = 150
        self.assert_rejected(coverage, "verified PDF page count")

    def test_exact_root_fields_are_enforced(self) -> None:
        coverage = deepcopy(self.coverage)
        coverage["summary"] = {}
        self.assert_rejected(coverage, "coverage root has unknown fields")

    def test_generated_report_is_synchronized(self) -> None:
        expected = render_theory_coverage_report(
            self.coverage, self.curriculum
        )
        self.assertEqual(OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
