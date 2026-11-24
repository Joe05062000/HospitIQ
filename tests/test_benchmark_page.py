"""Streamlit smoke checks for the enterprise shell and comparison workflow."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from strategy_models.benchmark import THEMES

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class BenchmarkPageTests(unittest.TestCase):
    def test_overview_dashboard_has_coverage_and_navigation(self) -> None:
        app = AppTest.from_file(APP).run()
        self.assertFalse(app.exception)
        self.assertEqual([item.value for item in app.metric], ["4", "16", "6", "21"])
        self.assertTrue(any("hgi-header" in element.proto.body for element in app.get("html")))
        self.assertEqual(len(app.get("vega_lite_chart")), 3)

    def test_selection_theme_and_download(self) -> None:
        app = AppTest.from_file(APP).run().switch_page("app_pages/competitive_benchmarking.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Competitive Benchmarking")
        self.assertEqual(len(app.multiselect(key="benchmark_companies").value), 4)
        self.assertEqual(app.get("download_button")[0].proto.label, "Download executive comparison")
        self.assertTrue(any("capability-matrix" in element.proto.body for element in app.get("html")))

        app.multiselect(key="benchmark_companies").set_value(["oracle"]).run()
        self.assertFalse(app.exception)
        self.assertIn("Select at least two", app.info[0].value)
        self.assertFalse(app.get("download_button"))

        app.multiselect(key="benchmark_companies").set_value(["mews", "siteminder"]).run()
        theme = next(item for item in THEMES if item.name == "Hotel distribution")
        app.selectbox(key="benchmark_theme").select(theme).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Mews and SiteMinder announce distribution partnership" == panel.label
                            for panel in app.expander))
        self.assertEqual(len(app.get("download_button")), 1)
