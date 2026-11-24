"""Parse customer portfolio CSV content in memory without external calls."""

import csv
import io
from collections.abc import Collection
from dataclasses import dataclass

from strategy_models.growth_research import SEGMENTS, Dimension

MAX_BYTES = 1_000_000
MAX_ROWS = 500
HEADERS = (
    "customer_id", "hotel_segment", "organization_segment", "property_type",
    "property_size", "geography", "existing_products", "eligible_products",
    "ineligible_products", "commercial_opportunity_notes",
)
TEMPLATE = ",".join(HEADERS) + "\n"
SYNTHETIC_CSV = TEMPLATE + (
    "DEMO-001,,independent,luxury,72,Demo region,mews-pms,mews-pay|mews-journey,,Synthetic discovery case\n"
    "DEMO-002,,small-group,limited-service,180,Demo region,mews-pms|mews-pay,mews-rms,mews-journey,Synthetic eligibility check\n"
    "DEMO-003,,large-chain,resort,460,Demo region,,mews-journey,,Synthetic ownership gap\n"
    "DEMO-004,,independent,limited-service,45,Demo region,-,mews-pms|mews-pay,,Synthetic complete empty ownership list\n"
)


class PortfolioError(ValueError):
    """The portfolio input does not conform to the documented schema."""


@dataclass(frozen=True)
class Customer:
    id: str | None = None
    organization: str | None = None
    property_type: str | None = None
    size: int | None = None
    geography: str | None = None
    owned: frozenset[str] | None = None
    eligible: frozenset[str] = frozenset()
    ineligible: frozenset[str] = frozenset()
    notes: str | None = None

    def segment(self, dimension: Dimension) -> str | None:
        return self.organization if dimension == "organization" else self.property_type


def parse_ids(value: str, allowed: Collection[str], field: str) -> frozenset[str]:
    if not value or value == "-":
        return frozenset()
    ids = [entry.strip() for entry in value.split("|")]
    if len(ids) != len(set(ids)) or any(entry not in allowed for entry in ids):
        raise PortfolioError(f"{field} must contain distinct catalog product IDs separated by |")
    return frozenset(ids)


def segment_id(value: str, dimension: Dimension | None = None) -> str | None:
    if not value:
        return None
    accepted = {item.label.casefold(): item.id for item in SEGMENTS.values()}
    key = accepted.get(value.casefold(), value.casefold())
    if key not in SEGMENTS or (dimension and SEGMENTS[key].dimension != dimension):
        raise PortfolioError(f"Use a documented {dimension or 'hotel'} segment ID or label")
    return key


def parse_customer(row: dict[str, str], product_ids: Collection[str]) -> Customer:
    organization = segment_id(row.get("organization_segment", ""), "organization")
    property_type = segment_id(row.get("property_type", ""), "property")
    legacy = segment_id(row.get("hotel_segment", ""))
    if legacy:
        dimension = SEGMENTS[legacy].dimension
        explicit = organization if dimension == "organization" else property_type
        if explicit and explicit != legacy:
            raise PortfolioError("hotel_segment conflicts with the explicit segment field")
        if dimension == "organization":
            organization = legacy
        else:
            property_type = legacy

    size_text = row.get("property_size", "")
    if size_text and (not size_text.isascii() or not size_text.isdigit() or len(size_text) > 6 or int(size_text) < 1):
        raise PortfolioError("property_size must be a positive whole number of rooms (up to six digits)")
    owned = row.get("existing_products", "")
    eligible = parse_ids(row.get("eligible_products", ""), product_ids, "eligible_products")
    ineligible = parse_ids(row.get("ineligible_products", ""), product_ids, "ineligible_products")
    if eligible & ineligible:
        raise PortfolioError("A product cannot be both eligible and ineligible")
    return Customer(
        id=row.get("customer_id") or None,
        organization=organization,
        property_type=property_type,
        size=int(size_text) if size_text else None,
        geography=row.get("geography") or None,
        owned=parse_ids(owned, product_ids, "existing_products") if owned else None,
        eligible=eligible,
        ineligible=ineligible,
        notes=row.get("commercial_opportunity_notes") or None,
    )


def parse_portfolio(data: bytes, product_ids: Collection[str]) -> tuple[Customer, ...]:
    if len(data) > MAX_BYTES:
        raise PortfolioError("The CSV exceeds the 1 MB limit")
    customers: list[Customer] = []
    ids = set()
    try:
        csv_file = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        header = [name.strip() for name in next(csv_file, [])]
        if not header or len(header) != len(set(header)) or set(header) - set(HEADERS):
            raise PortfolioError("Use unique column names from the supplied CSV template")
        for cells in csv_file:
            if not any(cells):
                continue
            try:
                if len(cells) != len(header):
                    raise PortfolioError("The number of values does not match the header")
                row = dict(zip(header, (cell.strip() for cell in cells), strict=True))
                if not any(row.values()):
                    continue
                if any(len(value) > 1000 or "\x00" in value for value in row.values()):
                    raise PortfolioError("Fields must contain at most 1,000 characters and no NUL bytes")
                if len(customers) >= MAX_ROWS:
                    raise PortfolioError(f"The CSV exceeds the {MAX_ROWS}-row limit")
                customer = parse_customer(row, product_ids)
                if customer.id:
                    if customer.id in ids:
                        raise PortfolioError("Duplicate customer_id")
                    ids.add(customer.id)
                customers.append(customer)
            except PortfolioError as exc:
                raise PortfolioError(f"Line {csv_file.line_num}: {exc}") from exc
    except (UnicodeError, csv.Error) as exc:
        raise PortfolioError("Use a valid UTF-8 CSV file with properly quoted fields") from exc
    if not customers:
        raise PortfolioError("Include at least one populated customer row")
    return tuple(customers)
