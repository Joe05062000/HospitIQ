"""Validation, filtering, and research review tests."""

import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from data_services.market_catalog import (
    CATALOG_PATH,
    CatalogError,
    MarketCatalog,
    url_key,
)
from data_services.research_refresh import record_review


class MarketCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_company_fields_and_relationships(self) -> None:
        catalog = MarketCatalog.from_dict(self.raw)
        self.assertEqual(catalog.evidence_status(catalog.companies["oracle"].source_ids), "verified")
        self.assertIn("opera-pms", {product.id for product in catalog.company_products("oracle")})
        self.assertEqual(catalog.company_products("unknown"), [])

        self.raw["products"][0]["company_id"] = "unknown"
        with self.assertRaisesRegex(CatalogError, "unknown ID"):
            MarketCatalog.from_dict(self.raw)
        self.raw["products"][0]["company_id"] = "oracle"

        self.raw["companies"][0]["official_name"] = " "
        with self.assertRaisesRegex(CatalogError, "official name"):
            MarketCatalog.from_dict(self.raw)

    def test_source_url_validation(self) -> None:
        self.assertEqual(
            url_key("https://www.example.com/news/?utm_source=x#section"),
            url_key("https://example.com/news"),
        )
        for url in (
            "http://example.com", "https://localhost", "https://a.internal",
            "https://127.0.0.1/", "https://user@example.com", "https://example.com:bad",
            "https://bad domain.com", "javascript:alert(1)", "https://example.com\\other",
        ):
            with self.subTest(url=url), self.assertRaises(CatalogError):
                url_key(url)

    def test_sources_require_valid_links_and_review_dates(self) -> None:
        source = self.raw["sources"][0]
        source["reviewed_at"] = None
        with self.assertRaisesRegex(CatalogError, "review timestamp"):
            MarketCatalog.from_dict(self.raw)
        source["status"] = "unverified"
        self.raw["products"][0]["source_ids"].append("unknown-evidence")
        with self.assertRaisesRegex(CatalogError, "unknown ID"):
            MarketCatalog.from_dict(self.raw)

    def test_duplicate_source_and_development_detection(self) -> None:
        original = self.raw["sources"][0]
        duplicate = {**original, "id": "other-source", "url": original["url"] + "?utm_campaign=test"}
        self.raw["sources"].append(duplicate)
        with self.assertRaisesRegex(CatalogError, "Duplicate source URL"):
            MarketCatalog.from_dict(self.raw)
        self.raw["sources"].pop()

        original = self.raw["developments"][0]
        self.raw["developments"].append({**original, "id": "repeat-development"})
        with self.assertRaisesRegex(CatalogError, "Duplicate development"):
            MarketCatalog.from_dict(self.raw)

    def test_filters_use_publication_dates_and_count_joint_event_once(self) -> None:
        catalog = MarketCatalog.from_dict(self.raw)
        self.assertEqual(
            [item.id for item in catalog.filter_developments(
                companies={"mews", "siteminder"}, themes={"partnerships"},
                start=date(2026, 5, 27), end=date(2026, 5, 27),
            )],
            ["mews-siteminder"],
        )
        self.assertEqual(
            [item.id for item in catalog.filter_developments(themes={"retailing"})],
            ["mews-winter"],
        )
        self.assertEqual(catalog.filter_developments(start=date(2026, 11, 23)), [])
        self.assertEqual(catalog.theme_coverage()["partnerships"], 2)

    def test_missing_and_unverified_evidence(self) -> None:
        self.raw["companies"][0]["source_ids"] = []
        source = next(item for item in self.raw["sources"] if item["id"] == "oracle-assistant")
        source.update(status="unavailable", published_on=None, reviewed_at=None)
        catalog = MarketCatalog.from_dict(self.raw)
        self.assertEqual(catalog.evidence_status(catalog.companies["oracle"].source_ids), "unverified")
        self.assertEqual(catalog.evidence_status(["oracle-assistant"]), "unavailable")
        self.assertIsNone(catalog.sources["oracle-assistant"].verified_at)
        self.assertEqual(len(catalog.filter_developments(companies={"oracle"})), 1)
        self.assertEqual(catalog.filter_developments(companies={"oracle"}, verified_only=True), [])
        self.assertEqual(
            catalog.filter_developments(companies={"oracle"}, end=date(2026, 11, 23)), []
        )

    def test_manual_review_validates_before_writing(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(self.raw), encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaisesRegex(CatalogError, "Inspect the original"):
                record_review(path, "oracle-assistant", "verified", "Pending", inspected=False)
            self.assertEqual(path.read_bytes(), before)

            updated = record_review(
                path, "oracle-assistant", "unavailable", "Publisher unavailable", inspected=False
            )
            self.assertEqual(len(updated.filter_developments(verified_only=True)), 5)
            source = updated.sources["oracle-assistant"]
            self.assertEqual(source.published_on, "2026-06-16")
            self.assertEqual(source.review_note, "Publisher unavailable")
            self.assertEqual(
                MarketCatalog.from_dict(json.loads(path.read_text(encoding="utf-8"))),
                updated,
            )
