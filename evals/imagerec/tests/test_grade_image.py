#!/usr/bin/env python3
"""
Unit tests for evals/imagerec/grade_image.py.

Run with:
    python -m pytest evals/imagerec/tests/ -v
or:
    python -m unittest discover -s evals/imagerec/tests -v
"""
import sys
import os
import unittest

# Allow running from repo root or from this directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from grade_image import (
    check_image_format,
    image_accuracy,
    CountResult,
    ALLOWED_RELATIONS,
)

CLF_SPEC = {"sub_type": "single_label_classification"}
CNT_SPEC = {"sub_type": "counting"}
SPT_SPEC = {"sub_type": "spatial_relation"}

# Also accept the task_type aliases used in the YAML files.
CLF_SPEC_ALT = {"task_type": "single_label_classification"}
CNT_SPEC_ALT = {"task_type": "counting"}
SPT_SPEC_ALT = {"task_type": "spatial_relation"}


class TestCheckImageFormatClf(unittest.TestCase):
    """check_image_format: single_label_classification."""

    def test_happy_path(self):
        """Valid clf output: dict with string label."""
        self.assertTrue(check_image_format({"label": "bear"}, CLF_SPEC))

    def test_happy_path_json_string(self):
        """Valid clf output passed as raw JSON string."""
        self.assertTrue(check_image_format('{"label": "bear"}', CLF_SPEC))

    def test_happy_path_task_type_alias(self):
        """task_type key accepted as alias for sub_type."""
        self.assertTrue(check_image_format({"label": "bear"}, CLF_SPEC_ALT))

    def test_missing_label_key(self):
        """Wrong key name."""
        self.assertFalse(check_image_format({"prediction": "bear"}, CLF_SPEC))

    def test_label_not_string(self):
        """label must be a string, not int."""
        self.assertFalse(check_image_format({"label": 42}, CLF_SPEC))

    def test_label_not_string_list(self):
        """label must be a string, not a list."""
        self.assertFalse(check_image_format({"label": ["bear"]}, CLF_SPEC))


class TestCheckImageFormatCnt(unittest.TestCase):
    """check_image_format: counting."""

    def test_happy_path_int(self):
        """Valid count: plain int."""
        self.assertTrue(check_image_format({"count": 3}, CNT_SPEC))

    def test_happy_path_zero(self):
        """Zero is a valid integer count."""
        self.assertTrue(check_image_format({"count": 0}, CNT_SPEC))

    def test_malformed_string_count(self):
        """count as string '3' must be rejected -- per task spec type must be int."""
        self.assertFalse(check_image_format({"count": "3"}, CNT_SPEC))

    def test_malformed_nonnumeric_string(self):
        """count as non-numeric string."""
        self.assertFalse(check_image_format({"count": "three"}, CNT_SPEC))

    def test_malformed_bool_rejected(self):
        """bool is subclass of int in Python; must be explicitly rejected."""
        self.assertFalse(check_image_format({"count": True}, CNT_SPEC))
        self.assertFalse(check_image_format({"count": False}, CNT_SPEC))

    def test_malformed_float(self):
        """float count rejected."""
        self.assertFalse(check_image_format({"count": 3.0}, CNT_SPEC))

    def test_missing_count_key(self):
        """Missing count key."""
        self.assertFalse(check_image_format({"label": "3"}, CNT_SPEC))

    def test_task_type_alias(self):
        self.assertTrue(check_image_format({"count": 1}, CNT_SPEC_ALT))


class TestCheckImageFormatSpt(unittest.TestCase):
    """check_image_format: spatial_relation."""

    def test_happy_path_above(self):
        self.assertTrue(check_image_format({"relation": "above"}, SPT_SPEC))

    def test_happy_path_left_of_with_space(self):
        """YAML uses 'left of' with space, not 'left_of'."""
        self.assertTrue(check_image_format({"relation": "left of"}, SPT_SPEC))

    def test_happy_path_right_of_with_space(self):
        self.assertTrue(check_image_format({"relation": "right of"}, SPT_SPEC))

    def test_out_of_vocab_relation(self):
        """'next to' is not in ALLOWED_RELATIONS."""
        self.assertFalse(check_image_format({"relation": "next to"}, SPT_SPEC))

    def test_underscore_form_rejected(self):
        """'left_of' (underscore) does not match the space-separated YAML values."""
        self.assertFalse(check_image_format({"relation": "left_of"}, SPT_SPEC))

    def test_missing_relation_key(self):
        self.assertFalse(check_image_format({"label": "above"}, SPT_SPEC))

    def test_relation_not_string(self):
        self.assertFalse(check_image_format({"relation": 1}, SPT_SPEC))

    def test_task_type_alias(self):
        self.assertTrue(check_image_format({"relation": "above"}, SPT_SPEC_ALT))


class TestCheckImageFormatParsing(unittest.TestCase):
    """check_image_format: JSON parsing edge cases."""

    def test_invalid_json_string(self):
        self.assertFalse(check_image_format("not json at all", CLF_SPEC))

    def test_json_array_not_dict(self):
        self.assertFalse(check_image_format("[1, 2, 3]", CLF_SPEC))

    def test_empty_dict(self):
        self.assertFalse(check_image_format({}, CLF_SPEC))

    def test_none_output(self):
        self.assertFalse(check_image_format(None, CLF_SPEC))


class TestImageAccuracyClf(unittest.TestCase):
    """image_accuracy: clf sub-type. Returns float."""

    def test_exact_match(self):
        self.assertEqual(image_accuracy({"label": "bear"}, "bear", "clf"), 1.0)

    def test_case_insensitive(self):
        self.assertEqual(image_accuracy({"label": "  Bear  "}, "BEAR", "clf"), 1.0)

    def test_wrong_label(self):
        self.assertEqual(image_accuracy({"label": "dog"}, "bear", "clf"), 0.0)

    def test_ground_truth_as_dict(self):
        """Ground-truth passed as YAML sub-dict {"label": "bear"}."""
        self.assertEqual(image_accuracy({"label": "bear"}, {"label": "bear"}, "clf"), 1.0)

    def test_full_subtype_name(self):
        self.assertEqual(
            image_accuracy({"label": "bear"}, "bear", "single_label_classification"),
            1.0,
        )


class TestImageAccuracyCnt(unittest.TestCase):
    """image_accuracy: cnt sub-type. Returns CountResult."""

    def test_exact_match(self):
        r = image_accuracy({"count": 1}, 1, "cnt")
        self.assertIsInstance(r, CountResult)
        self.assertEqual(r.exact, 1.0)
        self.assertTrue(r.within_one)

    def test_off_by_one(self):
        r = image_accuracy({"count": 2}, 1, "cnt")
        self.assertEqual(r.exact, 0.0)
        self.assertTrue(r.within_one)

    def test_off_by_two(self):
        r = image_accuracy({"count": 3}, 1, "cnt")
        self.assertEqual(r.exact, 0.0)
        self.assertFalse(r.within_one)

    def test_zero_ground_truth(self):
        r = image_accuracy({"count": 0}, 0, "cnt")
        self.assertEqual(r.exact, 1.0)
        self.assertTrue(r.within_one)

    def test_ground_truth_as_dict(self):
        r = image_accuracy({"count": 1}, {"count": 1}, "cnt")
        self.assertEqual(r.exact, 1.0)

    def test_full_subtype_name(self):
        r = image_accuracy({"count": 5}, 5, "counting")
        self.assertEqual(r.exact, 1.0)


class TestImageAccuracySpt(unittest.TestCase):
    """image_accuracy: spt sub-type. Returns float."""

    def test_exact_match(self):
        self.assertEqual(image_accuracy({"relation": "above"}, "above", "spt"), 1.0)

    def test_mismatch(self):
        self.assertEqual(image_accuracy({"relation": "below"}, "above", "spt"), 0.0)

    def test_left_of_with_space(self):
        self.assertEqual(image_accuracy({"relation": "left of"}, "left of", "spt"), 1.0)

    def test_ground_truth_as_dict(self):
        self.assertEqual(
            image_accuracy({"relation": "above"}, {"relation": "above"}, "spt"),
            1.0,
        )

    def test_full_subtype_name(self):
        self.assertEqual(
            image_accuracy({"relation": "above"}, "above", "spatial_relation"),
            1.0,
        )


class TestAllowedRelations(unittest.TestCase):
    """Sanity checks on the ALLOWED_RELATIONS constant."""

    def test_all_yaml_values_covered(self):
        """The three ground_truth values from the problem YAMLs must be in the set."""
        for rel in ("above", "below", "left of", "right of"):
            self.assertIn(rel, ALLOWED_RELATIONS, f"'{rel}' missing from ALLOWED_RELATIONS")

    def test_underscore_forms_not_included(self):
        """Underscore forms from the design doc example are intentionally excluded."""
        self.assertNotIn("left_of", ALLOWED_RELATIONS)
        self.assertNotIn("right_of", ALLOWED_RELATIONS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
