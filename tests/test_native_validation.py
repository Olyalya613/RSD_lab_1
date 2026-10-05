"""Regression checks without PostgreSQL; benchmark results are not produced here."""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class Body:
    async def json(self):
        return {"name": "Ghost Location"}


class ValidationTests(unittest.TestCase):
    def fake_pool(self, row):
        cur = MagicMock()
        cur.execute.return_value.fetchone.return_value = row
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        manager = MagicMock()
        manager.__enter__.return_value = conn
        return manager

    def test_nonexistent_location_is_404_even_without_version(self):
        with patch.object(app.pool, "connection", return_value=self.fake_pool(None)):
            with self.assertRaises(app.HTTPException) as err:
                app.put_location(
                    "00000000-0000-0000-0000-000000000000", {"name": "Ghost Location"}
                )
            self.assertEqual(404, err.exception.status_code)

    def test_existing_location_requires_version(self):
        with patch.object(
            app.pool, "connection", return_value=self.fake_pool({"id": "id"})
        ):
            with self.assertRaises(app.HTTPException) as err:
                app.put_location(
                    "00000000-0000-0000-0000-000000000000", {"name": "Ghost Location"}
                )
            self.assertEqual(400, err.exception.status_code)

    def test_invalid_currency_is_rejected(self):
        with self.assertRaises(app.HTTPException):
            app.validate({"title": "Trip", "currency": "usd"}, "plan", True)

    def test_budget_precision_is_rejected(self):
        with self.assertRaises(app.HTTPException):
            app.validate({"name": "Location", "budget": 1.123}, "location", True)

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(app.HTTPException):
            app.validate(
                {"title": "Trip", "injected_column": "DROP TABLE"}, "plan", True
            )


if __name__ == "__main__":
    unittest.main()
