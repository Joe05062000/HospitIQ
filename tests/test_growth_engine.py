"""Commercial rule, evidence, and playbook tests."""

import unittest
from dataclasses import replace

from data_services.customer_portfolio import Customer
from data_services.market_catalog import load_catalog
from strategy_models.growth_engine import (
    DEFAULT_WEIGHTS,
    FACTORS,
    evaluate,
    prioritize,
    rank_candidates,
    weighted_score,
)
from strategy_models.growth_playbook import playbook_html, playbook_steps
from strategy_models.growth_research import (
    DIMENSIONS,
    SEGMENTS,
    complement,
    documented_integration,
    growth_products,
)


class GrowthEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog()
        self.payments = self.catalog.products["mews-pay"]

    def test_complementarity_is_bidirectional_and_distinct_from_compatibility(self) -> None:
        self.assertEqual(complement("pms", "payments"), complement("payments", "pms"))
        self.assertIsNone(complement("pms", "pms"))
        self.assertIsNotNone(complement("pms", "distribution"))
        self.assertIsNone(documented_integration(self.catalog, "opera-distribution", frozenset({"opera-pms"})))
        documented = documented_integration(self.catalog, "mews-pay", frozenset({"mews-pms"}))
        self.assertIsNotNone(documented)
        assert documented is not None
        self.assertEqual(documented[1].id, "mews-payments")
        self.catalog.sources["mews-payments"] = replace(
            self.catalog.sources["mews-payments"], status="unavailable"
        )
        self.assertIsNone(documented_integration(self.catalog, "mews-pay", frozenset({"mews-pms"})))
        self.assertNotIn("mews-pay", growth_products(self.catalog, "mews"))

    def test_segment_dimensions_are_separate(self) -> None:
        scenario = Customer(organization="small-group", property_type="resort")
        self.assertEqual(len(SEGMENTS), 6)
        self.assertEqual({key: sum(item.dimension == key for item in SEGMENTS.values())
                          for key in DIMENSIONS}, {"organization": 3, "property": 3})
        self.assertEqual(scenario.segment("organization"), "small-group")
        self.assertEqual(scenario.segment("property"), "resort")

    def test_owned_and_ineligible_products_are_excluded(self) -> None:
        for customer in (
            Customer(owned=frozenset({"mews-pay"}), eligible=frozenset({"mews-pay"})),
            Customer(owned=frozenset(), ineligible=frozenset({"mews-pay"})),
        ):
            with self.subTest(customer=customer):
                self.assertIsNone(evaluate(
                    self.catalog, customer, self.payments, "organization", DEFAULT_WEIGHTS, row=1
                ))

    def test_missing_ownership_and_eligibility_require_discovery(self) -> None:
        for customer in (
            Customer(eligible=frozenset({"mews-pay"})),
            Customer(owned=frozenset({"mews-pms"})),
        ):
            with self.subTest(customer=customer):
                item = evaluate(self.catalog, customer, self.payments, "organization", DEFAULT_WEIGHTS, row=1)
                assert item is not None
                self.assertEqual(item.readiness, "Discovery only")
                self.assertLess(item.factors["evidence"], 4)

        owned = frozenset({"mews-pms"})
        item = evaluate(
            self.catalog, Customer(organization="small-group", owned=owned, eligible=frozenset({"mews-pay"})),
            self.payments, "organization", DEFAULT_WEIGHTS, row=1,
        )
        assert item is not None
        self.assertEqual(item.readiness, "Pilot candidate")
        self.assertEqual(item.factors["evidence"], 4)
        self.assertEqual(item.factors["compatibility"], 4)
        self.assertEqual(item.sources[0].url, self.catalog.sources["mews-payments"].url)

    def test_public_compatibility_does_not_imply_customer_ownership(self) -> None:
        item = evaluate(
            self.catalog, Customer(organization="independent"), self.payments,
            "organization", DEFAULT_WEIGHTS, row=1, hypothetical_anchor="pms",
        )
        assert item is not None
        self.assertEqual(item.factors["compatibility"], 4)
        self.assertIn("Hypothetical anchor", item.compatibility)
        self.assertFalse(item.ownership_known)
        self.assertEqual(item.readiness, "Discovery only")

    def test_weights_math_determinism_and_aggregation(self) -> None:
        self.assertEqual(weighted_score(dict.fromkeys(FACTORS, 4), DEFAULT_WEIGHTS), 100)
        customers = (
            Customer(organization="independent"),
            Customer(organization="independent", owned=frozenset(), eligible=frozenset({"mews-pay"})),
        )
        products = (self.payments, self.catalog.products["mews-pms"])
        initial = rank_candidates(self.catalog, customers, products, "organization", DEFAULT_WEIGHTS)
        self.assertEqual(initial, rank_candidates(
            self.catalog, customers, products[::-1], "organization", DEFAULT_WEIGHTS
        ))
        with self.assertRaisesRegex(ValueError, "above zero"):
            rank_candidates(self.catalog, customers, products, "organization", dict.fromkeys(FACTORS, 0))
        ranked = prioritize(initial)
        paid = next(item for item in ranked if item.product.id == "mews-pay")
        self.assertEqual((paid.count, paid.pilot_count), (2, 1))
        self.assertEqual(paid.score, sum(item.score for item in initial if item.product.id == "mews-pay") / 2)
        legacy_weights = DEFAULT_WEIGHTS | {"evidence": 100, "compatibility": 100}
        refreshed = rank_candidates(self.catalog, customers, products, "organization", legacy_weights)
        self.assertEqual(initial, refreshed)
        scored = [item for item in initial if item.product.id == "mews-pay"]
        self.assertEqual(scored[0].score, scored[1].score)
        self.assertNotEqual(scored[0].factors["evidence"], scored[1].factors["evidence"])

    def test_playbook_is_aggregate_only_and_source_linked(self) -> None:
        customer = Customer(id="private-account", notes="<private>", geography="Private geography", organization="independent")
        candidates = rank_candidates(self.catalog, (customer,), (self.payments,), "organization", DEFAULT_WEIGHTS)
        priorities = prioritize(candidates)
        self.assertEqual(len(playbook_steps(priorities)), 3)
        report = playbook_html("Mews <test>", priorities, "Customer Portfolio Mode")
        self.assertIn("Mews &lt;test&gt;", report)
        self.assertIn(self.catalog.sources["mews-payments"].url, report)
        self.assertIn("payment and reconciliation exceptions", report)
        self.assertIn("Decision checkpoint", report)
        for raw_value in (customer.id, customer.notes, customer.geography):
            assert raw_value is not None
            self.assertNotIn(raw_value, report)
