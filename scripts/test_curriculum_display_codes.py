#!/usr/bin/env python3
"""Regression tests for canonical hierarchical curriculum display codes."""

from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from curriculum_yaml import load
from generate_curriculum_data import _browser_payload
from validate_curriculum import (
    EXPECTED_MODULE_DISPLAY_CODES,
    _validate_module_display_codes,
)


ROOT = Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "data" / "curriculum.yml"
CANONICAL_DISPLAY_CODES = {
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


class CurriculumDisplayCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data = load(CURRICULUM)
        if not isinstance(data, dict):
            raise AssertionError("curriculum root must be a mapping")
        domains = data.get("domains")
        modules = data.get("modules")
        if not isinstance(domains, list) or not isinstance(modules, list):
            raise AssertionError("curriculum domains and modules must be lists")
        cls.data = data
        cls.domains = domains
        cls.modules = modules

    def _errors_after(
        self,
        mutate: Callable[[dict[str, dict[str, Any]], dict[str, dict[str, Any]]], None],
    ) -> list[str]:
        domains = deepcopy(self.domains)
        modules = deepcopy(self.modules)
        domains_by_id = {
            domain["id"]: domain
            for domain in domains
            if isinstance(domain, dict) and isinstance(domain.get("id"), str)
        }
        modules_by_id = {
            module["id"]: module
            for module in modules
            if isinstance(module, dict) and isinstance(module.get("id"), str)
        }
        mutate(modules_by_id, domains_by_id)
        errors: list[str] = []
        _validate_module_display_codes(modules_by_id, domains_by_id, errors)
        return errors

    def assert_rejected(
        self,
        mutate: Callable[[dict[str, dict[str, Any]], dict[str, dict[str, Any]]], None],
        expected_error: str,
    ) -> None:
        errors = self._errors_after(mutate)
        self.assertTrue(
            any(expected_error in error for error in errors),
            f"expected error containing {expected_error!r}, found: {errors}",
        )

    def test_all_24_codes_match_the_exact_canonical_mapping(self) -> None:
        actual = {
            module["id"]: module.get("display_code")
            for module in self.modules
            if isinstance(module, dict) and isinstance(module.get("id"), str)
        }
        self.assertEqual(CANONICAL_DISPLAY_CODES, EXPECTED_MODULE_DISPLAY_CODES)
        self.assertEqual(CANONICAL_DISPLAY_CODES, actual)
        self.assertEqual(24, len(actual))
        self.assertEqual(24, len(set(actual.values())))
        self.assertTrue(
            all(
                isinstance(display_code, str) and display_code
                for display_code in actual.values()
            )
        )
        projected = {
            module["id"]: module.get("display_code")
            for module in _browser_payload(self.data)["modules"]
        }
        self.assertEqual(CANONICAL_DISPLAY_CODES, projected)
        self.assertEqual([], self._errors_after(lambda _modules, _domains: None))

    def test_duplicate_code_is_rejected(self) -> None:
        self.assert_rejected(
            lambda modules, _domains: modules["MOD-18"].__setitem__(
                "display_code",
                modules["MOD-17"]["display_code"],
            ),
            "duplicate display_code",
        )

    def test_malformed_and_single_digit_codes_are_rejected(self) -> None:
        for malformed in ("2.1", "02-01", "02.1", "0201"):
            with self.subTest(malformed=malformed):
                self.assert_rejected(
                    lambda modules, _domains, value=malformed: modules[
                        "MOD-02"
                    ].__setitem__("display_code", value),
                    "expected NN.NN",
                )

    def test_wrong_domain_prefix_is_rejected(self) -> None:
        self.assert_rejected(
            lambda modules, _domains: modules["MOD-17"].__setitem__(
                "display_code",
                "03.02",
            ),
            "does not match DOMAIN-02 order 02",
        )

    def test_local_numbering_gap_is_rejected(self) -> None:
        self.assert_rejected(
            lambda modules, _domains: modules["MOD-18"].__setitem__(
                "display_code",
                "02.04",
            ),
            "must be continuous from 01",
        )

    def test_local_position_mismatch_is_rejected(self) -> None:
        def swap_codes(
            modules: dict[str, dict[str, Any]],
            _domains: dict[str, dict[str, Any]],
        ) -> None:
            modules["MOD-17"]["display_code"], modules["MOD-18"]["display_code"] = (
                modules["MOD-18"]["display_code"],
                modules["MOD-17"]["display_code"],
            )

        self.assert_rejected(swap_codes, "does not match one-based position")

    def test_code_assigned_to_wrong_module_is_rejected(self) -> None:
        self.assert_rejected(
            lambda modules, _domains: modules["MOD-10"].__setitem__(
                "display_code",
                "02.02",
            ),
            "expected canonical code 09.01",
        )

    def test_missing_empty_and_unexpected_types_are_rejected(self) -> None:
        cases = (
            (
                "missing",
                lambda modules, _domains: modules["MOD-02"].pop("display_code"),
                "expected a string",
            ),
            (
                "empty",
                lambda modules, _domains: modules["MOD-02"].__setitem__(
                    "display_code",
                    "",
                ),
                "expected a non-empty string",
            ),
            (
                "integer",
                lambda modules, _domains: modules["MOD-02"].__setitem__(
                    "display_code",
                    201,
                ),
                "expected a string",
            ),
        )
        for label, mutate, expected_error in cases:
            with self.subTest(case=label):
                self.assert_rejected(mutate, expected_error)

    def test_spaces_and_technical_ids_are_rejected(self) -> None:
        self.assert_rejected(
            lambda modules, _domains: modules["MOD-02"].__setitem__(
                "display_code",
                "02.01 ",
            ),
            "spaces are not allowed",
        )
        self.assert_rejected(
            lambda modules, _domains: modules["MOD-02"].__setitem__(
                "display_code",
                "MOD-02",
            ),
            "must not use the technical module ID",
        )


if __name__ == "__main__":
    unittest.main()
