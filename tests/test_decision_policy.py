"""Counterfactual and boundary tests for the local decision policy."""

import unittest
from dataclasses import replace
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data_services.market_catalog import load_catalog
from strategy_models.advisor import QUESTIONS, FinancialSnapshot, build_public_brief
from strategy_models.advisor_report import executive_html
from strategy_models.decision_policy import INSUFFICIENT, Criteria, evaluate_decision
from strategy_models.executive_case import ASSUMPTIONS, build_case
from strategy_models.financial import compare_scenarios

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
PASSING = Criteria(
    investment_cap=1_000_000, downside_cap=1_500_000, payback_months=36,
    qualification="Confirmed for this scope",
)


class DecisionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.brief = build_public_brief(
            cls.catalog, "investment", ("oracle", "mews"), "independent", None, focus_product="mews-pay",
        )
        cls.case = build_case(cls.catalog)
        cls.snapshot = FinancialSnapshot(
            "mews-pay", "independent", "USD", "Fictional audit inputs", tuple(cls.case.results.items()),
            "Harborlight Payments (fictional)", cls.case.sensitivities, cls.case.uncertainty, "Base",
        )

    def test_all_six_questions_have_action_and_gate(self):
        for question in QUESTIONS:
            with self.subTest(question=question):
                brief = build_public_brief(self.catalog, question, ("oracle", "mews"), "independent", None)
                result = evaluate_decision(brief)
                self.assertTrue(result.action and result.next_actions and result.gates and result.sources)
                if question == "investment":
                    self.assertEqual(result.recommendation, INSUFFICIENT)
                elif question == "growth":
                    self.assertEqual(result.recommendation, "Prioritize")
                    self.assertIn("discovery", result.action)
                else:
                    self.assertEqual(result.recommendation, "Investigate further")
                if question == "market":
                    titles = [item.title for item in brief.findings if item.section == "market"]
                    self.assertEqual(titles, sorted(titles, key=str.casefold))
                    self.assertIn("listed alphabetically", result.rationale)

    def test_growth_evidence_matches_ranked_lead_even_with_a_different_case_focus(self):
        brief = build_public_brief(
            self.catalog, "growth", ("oracle", "mews"), "independent", None, focus_product="mews-pay",
        )
        decision = evaluate_decision(brief, self.snapshot)
        self.assertIn("OPERA Cloud Distribution", decision.action)
        self.assertTrue(decision.evidence[0].startswith("OPERA Cloud Distribution"))

    def test_mixed_case_can_pilot_within_limits_but_downside_gate_can_reverse_it(self):
        result = evaluate_decision(self.brief, self.snapshot, PASSING)
        self.assertEqual(result.recommendation, "Conduct a controlled pilot")
        self.assertTrue(any("1,206,250" in row for row in result.evidence))
        self.assertTrue(any("Adoption rates" in risk and "business stress" in risk for risk in result.risks))
        strict = evaluate_decision(self.brief, self.snapshot, replace(PASSING, downside_cap=1_000_000))
        self.assertEqual(strict.recommendation, "Redesign the opportunity")
        self.assertIn("Downside tolerance", strict.rationale)

    def test_same_opportunity_all_negative_defers(self):
        stress = {name: replace(row, investment=row.investment + 10_000_000) for name, row in ASSUMPTIONS.items()}
        shocked = replace(
            self.snapshot, scenarios=tuple(compare_scenarios(stress).items()),
            normalized_sensitivity=(), business_sensitivity=(), sensitivity_case=None,
        )
        decision = evaluate_decision(self.brief, shocked, PASSING)
        self.assertEqual(decision.recommendation, "Defer investment")
        self.assertIn("all end with negative", decision.rationale)

    def test_strong_economics_never_substitute_for_qualification(self):
        strong = {
            name: replace(row, investment=100_000, revenue_per_adopter=8_000, fixed_cost=50_000)
            for name, row in ASSUMPTIONS.items()
        }
        snapshot = replace(
            self.snapshot, scenarios=tuple(compare_scenarios(strong).items()),
            normalized_sensitivity=(), business_sensitivity=(), sensitivity_case=None,
        )
        self.assertTrue(all(result.ending_cash > 0 for _, result in snapshot.scenarios))
        self.assertEqual(evaluate_decision(self.brief, snapshot, PASSING).recommendation, "Conduct a controlled pilot")
        unknown = evaluate_decision(self.brief, snapshot, replace(PASSING, qualification="Unknown"))
        self.assertEqual(unknown.recommendation, "Investigate further")
        self.assertTrue(any(check.result == "Pending" and "Customer" in check.name for check in unknown.checks))
        self.assertEqual(
            evaluate_decision(self.brief, snapshot, replace(PASSING, qualification="Confirmed blocker")).recommendation,
            "Defer investment",
        )

    def test_payback_and_investment_limits_explain_the_reversal(self):
        for criteria, gate in (
            (replace(PASSING, payback_months=24), "Base payback"),
            (replace(PASSING, investment_cap=900_000), "Investment cap"),
        ):
            decision = evaluate_decision(self.brief, self.snapshot, criteria)
            self.assertEqual(decision.recommendation, "Redesign the opportunity")
            self.assertIn(gate, decision.rationale)

    def test_missing_conflicting_and_unmatched_evidence_abstains(self):
        for snapshot, criteria in (
            (None, PASSING),
            (replace(self.snapshot, scenarios=self.snapshot.scenarios[:-1]), PASSING),
            (replace(self.snapshot, product_id="oracle-pms"), PASSING),
            (self.snapshot, replace(PASSING, payback_months=None)),
            (self.snapshot, replace(PASSING, qualification="Conflicting evidence")),
        ):
            with self.subTest(snapshot=snapshot is not None, criteria=criteria):
                self.assertEqual(evaluate_decision(self.brief, snapshot, criteria).recommendation, INSUFFICIENT)
        single = build_public_brief(self.catalog, "competition", ("mews",), "independent", None)
        self.assertEqual(evaluate_decision(single).recommendation, INSUFFICIENT)

    def test_export_carries_the_decision_and_the_criteria_failure(self):
        decision = evaluate_decision(self.brief, self.snapshot, replace(PASSING, payback_months=24))
        html = executive_html(
            self.catalog, self.brief, self.brief.priority_order(), "Evidence-Based Mode", self.snapshot, decision,
        )
        self.assertIn("Redesign the opportunity", html)
        self.assertIn("Fail · Base payback", html)
        self.assertIn("Rerun all three cases and clear the failed checks before planning a pilot.", html)
        self.assertNotIn("Run a time-boxed pilot on supported configurations", html)
        self.assertIn("USD 647,808", html)
        self.assertIn("What could change the recommendation", html)

    def test_harborlight_public_handoff_changes_with_management_limit(self):
        app = AppTest.from_file(APP, default_timeout=15).run().switch_page("app_pages/executive_case_study.py").run()
        next(button for button in app.button if button.label == "Discuss the decision in Strategy Advisor").click().run()
        self.assertFalse(app.exception)
        self.assertIn(INSUFFICIENT, [item.value for item in app.subheader])
        app.switch_page("app_pages/ai_strategy_advisor.py").run()
        key = "mews-pay:independent:USD:True"
        app.number_input(key=f"decision_cap_{key}").set_value(1_000_000)
        app.number_input(key=f"decision_downside_{key}").set_value(1_500_000)
        app.number_input(key=f"decision_payback_{key}").set_value(36)
        app.selectbox(key=f"decision_evidence_{key}").select("Confirmed for this scope").run()
        self.assertIn("Conduct a controlled pilot", [item.value for item in app.subheader])
        app.number_input(key=f"decision_payback_{key}").set_value(24).run()
        self.assertIn("Redesign the opportunity", [item.value for item in app.subheader])
        self.assertTrue(any("Fail · Base payback" in item.value for item in app.markdown))
        self.assertTrue(any("647,808" in item.value for item in app.markdown))
