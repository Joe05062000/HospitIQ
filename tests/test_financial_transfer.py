"""Financial handoff only retains qualified aggregates and public metadata."""

import unittest
from dataclasses import replace

from data_services.customer_portfolio import Customer
from data_services.market_catalog import load_catalog
from strategy_models.financial_transfer import (
    opportunity_from_growth,
    validated_handoff,
)
from strategy_models.growth_engine import DEFAULT_WEIGHTS, prioritize, rank_candidates


class TransferTests(unittest.TestCase):
    def test_qualified_unique_non_adopters_only(self) -> None:
        catalog = load_catalog()
        product = catalog.products["mews-pay"]
        valid = Customer(
            id="qualified", organization="independent", owned=frozenset(), eligible=frozenset({product.id}),
        )
        customers = (
            valid,
            replace(valid, id="duplicate"),
            replace(valid, id="Duplicate "),
            replace(valid, id=None),
            replace(valid, id="unknown-owner", owned=None),
            replace(valid, id="unknown-eligibility", eligible=frozenset()),
            replace(valid, id="already-owner", owned=frozenset({product.id})),
            replace(valid, id="denied", ineligible=frozenset({product.id})),
            replace(valid, id="another-segment", organization="small-group"),
        )
        ranks = prioritize(rank_candidates(catalog, customers, (product,), "organization", DEFAULT_WEIGHTS))
        priority = next(item for item in ranks if item.segment == "independent")
        transfer = opportunity_from_growth(priority, customers, "organization", real_portfolio=True)
        self.assertEqual(transfer.known_eligible, 1)
        self.assertEqual(transfer.uncounted_qualifying_rows, 3)
        self.assertEqual(transfer.identifier, "mews-pay:independent")
        self.assertEqual(transfer.source_ids, ("mews-payments",))
        self.assertNotIn("qualified", repr(transfer))
        self.assertFalse(hasattr(transfer, "score"))
        self.assertEqual(validated_handoff(catalog, transfer), transfer)
        self.assertIsNone(validated_handoff(catalog, replace(transfer, category="pms")))
        self.assertIsNone(opportunity_from_growth(
            priority, customers, "organization", real_portfolio=False
        ).known_eligible)
        self.assertIsNone(opportunity_from_growth(
            priority, customers[4:8], "organization", real_portfolio=True
        ).known_eligible)
