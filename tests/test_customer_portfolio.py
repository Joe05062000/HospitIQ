"""CSV validation and local-only portfolio processing."""

import unittest
from unittest.mock import patch

from data_services.customer_portfolio import (
    SYNTHETIC_CSV,
    PortfolioError,
    parse_portfolio,
)
from data_services.market_catalog import load_catalog


class PortfolioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = load_catalog().products

    def test_optional_values_and_ownership_semantics(self) -> None:
        data = b"customer_id,hotel_segment,existing_products,property_size,geography\nA,resort,,120,\nB,small-group,-,,Demo\n"
        first, second = parse_portfolio(data, self.products)
        self.assertEqual((first.property_type, first.organization), ("resort", None))
        self.assertEqual(first.size, 120)
        self.assertIsNone(first.owned)
        self.assertIsNone(first.geography)
        self.assertEqual(second.owned, frozenset())
        self.assertEqual(second.organization, "small-group")
        self.assertIsNone(second.size)

    def test_malformed_csv_is_rejected_with_safe_messages(self) -> None:
        for data in (
            b"bad_header\nvalue\n",
            b"customer_id,customer_id\nA,B\n",
            b"customer_id,property_size\nA,0\n",
            b"property_size\n12.3\n",
            b"customer_id,organization_segment\nA,resort\n",
            b"hotel_segment,organization_segment\nindependent,small-group\n",
            b"customer_id\nA\nA\n",
            b"existing_products\nmade-up-product\n",
            b"eligible_products,ineligible_products\nmews-pay,mews-pay\n",
            b"geography\n\"unclosed\n",
            b"customer_id\n\xff\n",
            b"customer_id\n",
            b"customer_id\n" + b"A" * 1_000_001,
            b"customer_id\n" + b"\n".join(str(n).encode() for n in range(501)),
        ):
            with self.subTest(prefix=data[:60]), self.assertRaises(PortfolioError):
                parse_portfolio(data, self.products)

    def test_parser_requires_neither_disk_nor_network(self) -> None:
        with patch("builtins.open", side_effect=AssertionError("disk access")), patch(
            "socket.socket", side_effect=AssertionError("network access")
        ):
            customers = parse_portfolio(SYNTHETIC_CSV.encode(), self.products)
        self.assertEqual(len(customers), 4)
        self.assertTrue(all(customer.id and customer.id.startswith("DEMO-") for customer in customers))
