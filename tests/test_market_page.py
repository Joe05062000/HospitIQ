"""Streamlit smoke checks for real data, filters, and empty snapshots."""

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from data_services.market_catalog import CatalogError, MarketCatalog

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def open_market() -> AppTest:
    return AppTest.from_file(APP).run().switch_page("app_pages/market_intelligence.py").run()


class MarketPageTests(unittest.TestCase):
    def test_research_tabs_and_coverage_render(self) -> None:
        app = open_market()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Market Intelligence")
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["Industry Overview", "Company Explorer", "Industry Developments"],
        )
        self.assertEqual(app.metric[0].value, "4 / 4")
        self.assertEqual(app.metric[1].value, "6")
        self.assertEqual(app.metric[3].value, "Sep 22, 2026")
        app.selectbox(key="market_company").select("amadeus").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Demand360" in panel.label for panel in app.expander))

    def test_siteminder_finding_uses_reported_revenue_and_cites_primary_sources(self) -> None:
        app = open_market()
        self.assertFalse(app.exception)
        self.assertFalse(app.dataframe)
        app.selectbox(key="market_company").select("siteminder").run()
        self.assertTrue(any("SiteMinder |" in item.value for item in app.tabs[1].subheader))
        self.assertFalse(app.tabs[0].dataframe)
        history = app.dataframe[0].value
        self.assertEqual(history["Fiscal year"].tolist(), ["FY24", "FY25", "FY26"])
        self.assertEqual(history["Total (A$m)"].tolist(), ["190.673", "224.327", "266.061"])
        self.assertEqual(history["Transaction share"].tolist(), ["35.8%", "38.0%", "41.7%"])
        self.assertEqual(history["Monthly transaction ARPU (A$)"].tolist(), [132, 155, 179])
        for _, row in history.iterrows():
            self.assertAlmostEqual(
                float(row["Subscriptions (A$m)"]) + float(row["Transactions (A$m)"]),
                float(row["Total (A$m)"]),
                places=3,
            )
        body = "\n".join(item.value for item in app.markdown)
        self.assertIn("61.3% of FY26 reported revenue growth", body)
        self.assertIn("AUD 132 in FY24 to AUD 179 in FY26", body)
        self.assertIn("cannot isolate cross-sell uplift", body)
        self.assertIn("AUD 25.601 million", body)
        self.assertIn("AUD 41.734 million", body)
        self.assertIn("250827_FY25-Annual-Report.pdf", body)
        self.assertIn("Annual-Report-SiteMinder-FY26.pdf", body)
        self.assertIn("Annual-General-Meeting.pdf", body)

    def test_filters_render_matches_and_empty_state(self) -> None:
        app = open_market()
        app.multiselect(key="market_filter_themes").set_value(["retailing"]).run()
        self.assertFalse(app.exception)
        self.assertEqual(sum("1 of 6 announcements" in text.value for text in app.caption), 1)
        app.date_input(key="market_start").set_value(date(2026, 6, 16)).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No announcements match" in entry.value for entry in app.info))

    def test_empty_and_invalid_catalogs_render_helpful_states(self) -> None:
        empty = MarketCatalog({}, {}, {}, {}, {})
        with patch("data_services.market_catalog.load_catalog", return_value=empty):
            app = open_market()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, "0")
        self.assertTrue(any("Company profiles will appear" in entry.value for entry in app.info))

        with patch("data_services.market_catalog.load_catalog", side_effect=CatalogError("bad catalog")):
            app = open_market()
        self.assertFalse(app.exception)
        self.assertIn("could not be loaded", app.error[0].value)
