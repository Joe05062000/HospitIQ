"""Case narrative, exact financial handoff, and offline deployment checks."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from brand import CASE_STUDY_TITLE
from data_services.market_catalog import load_catalog
from strategy_models.advisor import FINANCIAL_BRIEF_KEY, build_public_brief
from strategy_models.executive_case import ASSUMPTIONS, PRODUCT, build_case
from strategy_models.executive_case_report import case_report
from strategy_models.financial import compare_scenarios

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
CASE = "app_pages/executive_case_study.py"


class ExecutiveCaseTests(unittest.TestCase):
    def test_case_projections_and_sources_match_engines(self) -> None:
        catalog = load_catalog()
        case = build_case(catalog)
        self.assertEqual(case.results, compare_scenarios(ASSUMPTIONS))
        self.assertEqual(case.results["Base"].years[0].new_adopters, 400)
        self.assertEqual(case.results["Base"].ending_cash, 647_808)
        self.assertEqual(case.results["Conservative"].ending_cash, -1_206_250)
        self.assertIsNone(case.results["Conservative"].payback_months)
        self.assertTrue(all(catalog.sources[item.source_id].status == "verified" for item in case.developments))
        self.assertTrue(all(source.status == "verified" for _, entries in case.payments_evidence
                            for item in entries for source in item.sources))
        html = case_report(catalog, case)
        for required in (
            f"<title>{CASE_STUDY_TITLE} · HospitIQ</title>",
            "Fictional company", "USD 647,808", "USD 4,579,680", "Proposed 90-day pilot",
            "Normalized sensitivity analysis", catalog.sources["mews-finance"].url, "Assumptions and methodology",
        ):
            self.assertIn(required, html)

    def test_case_route_download_and_financial_workspace_handoff(self) -> None:
        app = AppTest.from_file(APP, default_timeout=10).run()
        next(btn for btn in app.button if btn.label == "Explore the case study →").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, CASE_STUDY_TITLE)
        self.assertEqual(app.get("download_button")[0].proto.label, f"Download {CASE_STUDY_TITLE} briefing")
        self.assertEqual(len(app.get("plotly_chart")), 2)
        next(btn for btn in app.button if btn.label == "Open case in Financial Scenario Simulator").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="financial_opportunity_mode").value, CASE_STUDY_TITLE)
        self.assertEqual(app.number_input(key="financial_population_fictional-payments-case_Illustrative defaults_2000").value, 2000)
        self.assertTrue(any("647,808" in item.value for item in app.metric))
        self.assertTrue(any(item.value == PRODUCT for item in app.subheader))

    def test_offline_case_advisor_receives_engine_results_without_provider(self) -> None:
        with patch("data_services.nvidia_advisor.trial_enabled", return_value=False), patch(
            "data_services.nvidia_advisor.request_priorities"
        ) as provider:
            app = AppTest.from_file(APP, default_timeout=10).run().switch_page(CASE).run()
            next(btn for btn in app.button if btn.label == "Discuss the decision in Strategy Advisor").click().run()
            provider.assert_not_called()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="advisor_mode").options, ["Evidence-Based Mode"])
        self.assertEqual(app.selectbox(key="advisor_question").value, "investment")
        snapshot = app.session_state[FINANCIAL_BRIEF_KEY]
        self.assertEqual(dict(snapshot.scenarios), compare_scenarios(ASSUMPTIONS))
        self.assertEqual(snapshot.fictional_label, PRODUCT)
        self.assertTrue(any("647,808" in item.value for item in app.markdown))

    def test_lead_stays_relevant_and_does_not_invent_actions(self) -> None:
        catalog = load_catalog()
        brief = build_public_brief(catalog, "growth", ("oracle", "mews"), "independent", None)
        order = tuple(item.id for item in brief.findings if item.section != "growth")[:3]
        aligned = brief.align_priorities(order)
        self.assertTrue(aligned[0].startswith("growth-"))
        self.assertEqual(len(aligned), 1)
        self.assertTrue(set(aligned) <= {item.id for item in brief.findings})
