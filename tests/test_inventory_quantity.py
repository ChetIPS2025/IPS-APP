"""Unit tests for inventory whole-number quantity helpers."""

from __future__ import annotations

import unittest

from app.utils.inventory_quantity import (
    format_inventory_quantity,
    inventory_qty_input_kwargs,
    parse_inventory_quantity,
    read_inventory_quantity,
    try_parse_inventory_quantity,
)


class TestInventoryQuantity(unittest.TestCase):
    def test_parse_whole_number_int(self) -> None:
        self.assertEqual(parse_inventory_quantity(25), 25)

    def test_parse_whole_number_float(self) -> None:
        self.assertEqual(parse_inventory_quantity(25.0), 25)

    def test_reject_decimal_float(self) -> None:
        with self.assertRaises(ValueError):
            parse_inventory_quantity(25.5)

    def test_reject_decimal_string(self) -> None:
        with self.assertRaises(ValueError):
            parse_inventory_quantity("25.25")

    def test_reject_negative_by_default(self) -> None:
        with self.assertRaises(ValueError):
            parse_inventory_quantity(-1)

    def test_allow_negative_when_enabled(self) -> None:
        self.assertEqual(parse_inventory_quantity(-3, allow_negative=True), -3)

    def test_try_parse_returns_error(self) -> None:
        qty, err = try_parse_inventory_quantity(2.5, allow_zero=False)
        self.assertIsNone(qty)
        self.assertIn("whole number", str(err))

    def test_format_inventory_quantity_no_decimals(self) -> None:
        self.assertEqual(format_inventory_quantity(25.0), "25")
        self.assertEqual(format_inventory_quantity(25.0, "EA"), "25 EA")

    def test_read_inventory_quantity_from_row(self) -> None:
        row = {"qty_on_hand": 12, "quantity_on_hand": 99}
        self.assertEqual(read_inventory_quantity(row, "qty_on_hand", "quantity_on_hand"), 12)

    def test_inventory_qty_input_kwargs(self) -> None:
        kwargs = inventory_qty_input_kwargs(min_value=1, value=3.0)
        self.assertEqual(kwargs["step"], 1)
        self.assertEqual(kwargs["format"], "%d")
        self.assertEqual(kwargs["value"], 3)


if __name__ == "__main__":
    unittest.main()
