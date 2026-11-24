"""Cohort accounting, sensitivity and export regression checks."""

import unittest
from dataclasses import replace

from data_services.market_catalog import load_catalog
from strategy_models.financial import (
    SCENARIOS,
    AssumptionError,
    Assumptions,
    aligned_launch,
    business_uncertainty,
    compare_scenarios,
    payback_label,
    sensitivity,
    simulate,
)
from strategy_models.financial_report import (
    annual_rows,
    briefing_html,
    money,
    rollout_payback,
)
from strategy_models.financial_transfer import Opportunity

BASE = Assumptions(100, (0.5, 0.5, 1), 1_000, 0.6, 5_000, 30_000, 1, 0.8)


class FinancialTests(unittest.TestCase):
    def test_three_year_cohorts_costs_and_cash(self) -> None:
        result = simulate(BASE)
        year1, year2, year3 = result.years
        self.assertEqual([row.new_adopters for row in result.years], [50, 25, 25])
        self.assertEqual([row.active_adopters for row in result.years], [50, 65, 77])
        self.assertEqual([row.retained_adopters for row in result.years], [0, 40, 52])
        self.assertEqual([row.churned_adopters for row in result.years], [0, 10, 13])
        self.assertEqual([row.remaining for row in result.years], [50, 25, 0])
        self.assertEqual([row.revenue for row in result.years], [50_000, 65_000, 77_000])
        self.assertEqual(result.total_revenue, 192_000)
        self.assertEqual(year1.variable_cost, 20_000)
        self.assertEqual(year1.contribution_profit, 30_000)
        self.assertEqual(year1.fixed_cost, 5_000)
        self.assertEqual(year1.investment, 30_000)
        self.assertEqual(year1.operating_contribution, 25_000)
        self.assertEqual(year1.cash_contribution, -5_000)
        self.assertEqual(year2.investment, 0)
        self.assertEqual(year3.cumulative_cash, 70_200)
        self.assertEqual(result.ending_cash, 70_200)
        self.assertAlmostEqual(result.payback_months or 0, 12 + 12 * 5_000 / 34_000)

    def test_display_rounds_customer_counts_without_changing_revenue(self) -> None:
        result = simulate(replace(BASE, eligible=101, activation="Mid-year"))
        rows = {label: values for label, *values in annual_rows(result, "USD")}
        self.assertEqual(result.years[0].new_adopters, 50.5)
        self.assertEqual(result.years[0].revenue, 25_250)
        self.assertEqual(rows["New adopters"][0], "50")
        self.assertEqual(rows["Incremental revenue"][0], "USD 25,250")

    def test_rollout_delays_all_activity_and_payback_clock(self) -> None:
        result = simulate(replace(BASE, rollout_year=2, investment=12_500))
        self.assertEqual([row.new_adopters for row in result.years], [0, 50, 50])
        self.assertEqual([row.fixed_cost for row in result.years], [0, 5_000, 5_000])
        self.assertEqual([row.investment for row in result.years], [0, 12_500, 0])
        self.assertEqual(result.payback_months, 6.0)
        self.assertEqual(rollout_payback(result), "Approx. 6 months · Year 2 launch")

    def test_midyear_recognition_and_payback_recover_only_after_activation(self) -> None:
        result = simulate(replace(
            BASE, activation="Mid-year", adoption=(1, 0, 0), margin=1.0, investment=20_000, fixed_cost=10_000,
        ))
        self.assertEqual(result.years[0].revenue, 50_000)
        self.assertEqual(result.years[1].revenue, 80_000)
        self.assertEqual(result.years[0].cash_contribution, 20_000)
        self.assertAlmostEqual(result.payback_months or 0, 6 + 6 * 25_000 / 45_000)

    def test_normalized_rates_and_explicit_ranges_use_same_engine(self) -> None:
        drivers = {item.driver: item for item in sensitivity(BASE, .10)}
        adoption_low = simulate(replace(BASE, adoption=(.45, .45, .90))).ending_cash
        self.assertAlmostEqual(drivers["Adoption rates"].low, adoption_low)
        self.assertAlmostEqual(drivers["Fixed operating costs"].low_change, 1_500)
        stress = business_uncertainty(BASE, {"Adoption rates": (-.3, .05)})[0]
        self.assertLess(stress.low, adoption_low)

    def test_aligned_launch_preserves_calendar_inputs_and_marks_prelaunch(self) -> None:
        cases = dict.fromkeys(SCENARIOS, BASE) | {"Conservative": replace(BASE, rollout_year=2)}
        self.assertIsNone(cases["Conservative"].active_adoption[0])
        common = aligned_launch(cases, 1)
        self.assertEqual(common["Conservative"], common["Base"])

    def test_full_churn_never_reopens_adoption_pool(self) -> None:
        result = simulate(replace(BASE, adoption=(1, 1, 1), retention=0))
        self.assertEqual([row.active_adopters for row in result.years], [100, 0, 0])
        self.assertEqual([row.new_adopters for row in result.years], [100, 0, 0])
        self.assertGreaterEqual(min(row.remaining for row in result.years), 0)

    def test_payback_absent_or_no_investment(self) -> None:
        self.assertIsNone(simulate(replace(BASE, eligible=0)).payback_months)
        self.assertEqual(payback_label(simulate(replace(BASE, investment=0))), "No upfront investment")
        self.assertEqual(
            payback_label(simulate(replace(BASE, rollout_year=3, investment=1e8))),
            "Not reached within 3 years",
        )

    def test_missing_and_invalid_assumptions(self) -> None:
        for invalid in (
            replace(BASE, eligible=-1), replace(BASE, adoption=(0, 1, 1.01)),
            replace(BASE, margin=float("nan")), replace(BASE, retention=-1),
            replace(BASE, investment=-1), replace(BASE, rollout_year=4),
        ):
            with self.subTest(value=invalid), self.assertRaises(AssumptionError):
                simulate(invalid)
        with self.assertRaises(AssumptionError):
            compare_scenarios({"Base": BASE})
        with self.assertRaisesRegex(AssumptionError, "shared eligible"):
            compare_scenarios(dict.fromkeys(SCENARIOS, BASE) | {"Base": replace(BASE, eligible=1)})

    def test_scenario_sensitivity_and_export(self) -> None:
        results = compare_scenarios({
            "Conservative": replace(BASE, margin=0.3), "Base": BASE,
            "Ambitious": replace(BASE, revenue_per_adopter=2_000),
        })
        self.assertEqual(tuple(results), SCENARIOS)
        self.assertLess(results["Conservative"].ending_cash, results["Base"].ending_cash)
        self.assertGreater(results["Ambitious"].ending_cash, results["Base"].ending_cash)
        drivers = sensitivity(BASE, 0.1)
        self.assertEqual(len(drivers), 6)
        self.assertEqual([round(item.absolute_impact, 2) for item in drivers],
                         sorted((round(item.absolute_impact, 2) for item in drivers), reverse=True))
        investment = next(item for item in drivers if item.driver == "One-time investment")
        self.assertAlmostEqual(investment.low_change, 3_000)
        self.assertAlmostEqual(investment.high_change, -3_000)
        retention = next(item for item in drivers if item.driver == "Retention")
        self.assertLess(retention.low_change, 0)
        self.assertGreater(retention.high_change, 0)

        catalog = load_catalog()
        opp = Opportunity("mews-pay", "payments", "independent", ("mews-payments",))
        html = briefing_html(catalog, opp, results, "Base", drivers, "USD", "Illustrative inputs", 0.1)
        self.assertIn(money(results["Base"].ending_cash, "USD"), html)
        self.assertIn(catalog.sources["mews-payments"].url, html)
        self.assertIn("Decision checkpoints", html)
        self.assertIn("Illustrative inputs", html)
        self.assertIn("Applied adoption", html)
