"""Decision-specific Advisor, provenance, financial timing, and mode guards."""

import unittest
from datetime import UTC
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from data_services.market_catalog import load_catalog
from data_services.nvidia_advisor import (
    NvidiaError,
    NvidiaSettings,
    request_priorities,
    trial_enabled,
)
from strategy_models.advisor import QUESTIONS, build_public_brief
from strategy_models.executive_case import CONSERVATIVE_TIMING, build_case
from strategy_models.executive_case_report import case_report

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class PredeploymentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog()

    def test_each_question_has_only_matching_primary_answers(self) -> None:
        for question in QUESTIONS:
            with self.subTest(question=question):
                brief = build_public_brief(self.catalog, question, ("oracle", "mews"), "independent", None)
                answers = [item for item in brief.findings if item.id in brief.priority_order()]
                self.assertTrue(answers)
                self.assertTrue(all(item.section == question and item.sources and item.action for item in answers))
        risk = build_public_brief(self.catalog, "cross-sell", ("mews",), "independent", None)
        answers = [item for item in risk.findings if item.id in risk.priority_order()]
        self.assertEqual(len(answers), 3)
        self.assertTrue(all(item.assumption and item.metric for item in answers))
        self.assertIn("Mews Payments", answers[0].title)

    def test_differentiation_is_evidence_backed_and_insufficiency_has_no_fallback_ranking(self) -> None:
        brief = build_public_brief(self.catalog, "competition", ("oracle", "mews"), "independent", None)
        answer = next(item for item in brief.findings if item.id == brief.priority_order()[0])
        self.assertIn("Opportunity to test", answer.interpretation)
        self.assertEqual({source.id for source in answer.sources}, {"oracle-assistant", "mews-winter"})
        single = build_public_brief(self.catalog, "competition", ("mews",), "independent", None)
        self.assertEqual(single.priority_order(), ())

    def test_provenance_on_both_pages(self) -> None:
        reviewed = [source.verified_at for source in self.catalog.sources.values() if source.verified_at]
        stamp = max(reviewed).astimezone(UTC).strftime("%B %d, %Y").replace(" 0", " ")
        for script in ("market_intelligence", "competitive_benchmarking"):
            with self.subTest(page=script):
                app = AppTest.from_file(APP, default_timeout=10).run().switch_page(f"app_pages/{script}.py").run()
                self.assertFalse(app.exception)
                self.assertTrue(any(f"as of {stamp} · 4 verified vendors · 6 verified announcements" in item.value
                                    for item in app.markdown))

    def test_conservative_cash_timing_is_reconciled_to_case_export(self) -> None:
        case = build_case(self.catalog)
        result = case.results["Conservative"]
        self.assertEqual([item.investment for item in result.years], [0, 1_000_000, 0])
        self.assertEqual([item.fixed_cost for item in result.years], [0, 420_000, 420_000])
        self.assertEqual(result.years[0].cash_contribution, 0)
        self.assertEqual(result.ending_cash, -1_206_250)
        self.assertIn(CONSERVATIVE_TIMING, case_report(self.catalog, case))

    def test_public_release_blocks_private_flags_and_hides_upload(self) -> None:
        with patch.dict("os.environ", {"HGI_DEPLOYMENT_MODE": "private", "HGI_ENABLE_NVIDIA_TRIAL": "1"}), patch(
            "data_services.nvidia_advisor.build_opener"
        ) as opener:
            self.assertFalse(trial_enabled())
            brief = build_public_brief(self.catalog, "market", ("mews",), "independent", None)
            with self.assertRaisesRegex(NvidiaError, "disabled"):
                request_priorities(brief, NvidiaSettings("fake-fixture"))
            opener.assert_not_called()
            app = AppTest.from_file(APP, default_timeout=10).run().switch_page("app_pages/ai_strategy_advisor.py").run()
            self.assertEqual(app.radio(key="advisor_mode").options, ["Evidence-Based Mode"])
            app.switch_page("app_pages/product_growth_intelligence.py").run()
            app.radio(key="growth_mode").set_value("Customer Portfolio Mode").run()
            self.assertFalse(app.get("file_uploader"))
            self.assertEqual(app.radio(key="growth_input_kind").options, ["Synthetic demonstration"])
