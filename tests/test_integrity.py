"""Cross-workspace evidence and ranking consistency."""

import unittest
from dataclasses import replace
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data_services.market_catalog import load_catalog
from strategy_models.advisor import build_public_brief
from strategy_models.benchmark import capability_cells
from strategy_models.executive_case import build_case

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class IntegrityTests(unittest.TestCase):
    def test_beta_and_announcement_do_not_establish_general_availability(self) -> None:
        catalog = load_catalog()
        cell = capability_cells(catalog, "mews")["distribution"]
        self.assertEqual(cell.status, "Documented capability")
        self.assertEqual({item.stage for item in cell.evidence}, {
            "Existing integration", "Beta rollout", "Planned integration at announcement",
        })
        catalog.sources["mews-marketplace-doc"] = replace(catalog.sources["mews-marketplace-doc"], status="unavailable")
        self.assertEqual(capability_cells(catalog, "mews")["distribution"].status, "Announced or limited availability")

    def test_case_cash_impact_and_rankings(self) -> None:
        case = build_case(load_catalog())
        self.assertEqual(case.aligned["Conservative"].ending_cash, -1_080_550)
        self.assertEqual(case.results["Ambitious"].ending_cash, 1_800_741.4)
        normalized = {item.driver: item.absolute_impact for item in case.sensitivities}
        self.assertAlmostEqual(normalized["Revenue per adopter"], normalized["Contribution margin"])
        self.assertLess(normalized["Adoption rates"], normalized["Contribution margin"])
        self.assertEqual(case.uncertainty[0].driver, "Adoption rates")

    def test_default_growth_and_case_investment_focus_payments(self) -> None:
        catalog = load_catalog()
        brief = build_public_brief(catalog, "growth", ("mews",), "independent", None)
        self.assertEqual(brief.priority_order()[0], "growth-mews-pay")
        brief = build_public_brief(catalog, "investment", ("oracle", "mews"), "independent", None, focus_product="mews-pay")
        requirements = [item for item in brief.findings if item.section == "investment"]
        self.assertEqual(len(requirements), 3)
        self.assertEqual(requirements[0].title, "Qualify Mews Payments")
        self.assertIn("incumbent processor", requirements[0].action)
        self.assertIn("reconciliation exceptions", requirements[1].action)
        self.assertTrue(all(item.sources for item in requirements))

    def test_growth_handoff_respects_explicit_product_filter(self) -> None:
        app = AppTest.from_file(APP, default_timeout=10).run().switch_page(
            "app_pages/product_growth_intelligence.py"
        ).run()
        app.multiselect(key="growth_product_filter_mews").set_value(["mews-rms"]).run()
        app.button(key="growth_open_advisor").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Strategy Advisor")
        self.assertTrue(any("1. Mews Revenue Management" == item.value for item in app.subheader))
