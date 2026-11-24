"""Streamlit smoke tests for manual assumptions, charts and page transfer."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from strategy_models.financial_transfer import HANDOFF_KEY

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class FinancialPageTests(unittest.TestCase):
    def test_independent_demo_and_empty_manual_mode(self) -> None:
        app = AppTest.from_file(APP, default_timeout=10).run().switch_page("app_pages/financial_scenario_simulator.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Financial Scenario Simulator")
        self.assertEqual(len(app.get("plotly_chart")), 2)
        activation_key = "financial_opera-pms:unclassified_Base_demo_activation"
        self.assertEqual(app.selectbox(key=activation_key).value, "Mid-year")
        app.selectbox(key=activation_key).select("Beginning of year").run()
        app.switch_page("app_pages/market_intelligence.py").run()
        app.switch_page("app_pages/financial_scenario_simulator.py").run()
        self.assertEqual(app.selectbox(key=activation_key).value, "Beginning of year")
        self.assertTrue(any("Year 2 launch" in item.value for item in app.markdown))
        self.assertFalse(any("opera-pms:unclassified" in item.value for item in app.caption))
        self.assertEqual(app.get("download_button")[0].proto.label, "Download executive financial brief")
        app.radio(key="financial_input_mode").set_value("Enter assumptions").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("download_button"))
        self.assertFalse(app.get("plotly_chart"))
        self.assertTrue(any("Complete at least one scenario" in item.value for item in app.info))

    def test_alternatives_require_separate_eligible_population(self) -> None:
        app = AppTest.from_file(APP, default_timeout=10).run().switch_page("app_pages/financial_scenario_simulator.py").run()
        app.multiselect(key="financial_alts_opera-pms").set_value(["opera-pms", "mews-pay"]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Complete the eligible population" in item.value for item in app.caption))
        app.number_input(key="financial_alt_pop_opera-pms:unclassified_mews-pay").set_value(200).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Highest modeled three-year net cash" in item.value for item in app.markdown))
        self.assertTrue(any("Lowest upfront capital requirement" in item.value for item in app.markdown))

    def test_growth_button_opens_simulator_with_public_handoff(self) -> None:
        app = AppTest.from_file(APP, default_timeout=10).run().switch_page("app_pages/product_growth_intelligence.py").run()
        self.assertFalse(app.exception)
        transfer = next(button for button in app.button if button.label == "Open in Financial Simulator")
        transfer.click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Financial Scenario Simulator")
        self.assertEqual(app.radio(key="financial_opportunity_mode").value, "Product Growth handoff")
        opportunity = app.session_state[HANDOFF_KEY]
        self.assertIsNone(opportunity.known_eligible)
        self.assertTrue(opportunity.source_ids)
