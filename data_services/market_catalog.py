"""Load and validate the curated market intelligence snapshot."""

import ipaddress
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlsplit

CATALOG_PATH = Path(__file__).resolve().parents[1] / "research" / "market_catalog.json"
Status = Literal["verified", "unverified", "unavailable"]
STATUSES = ("verified", "unverified", "unavailable")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class CatalogError(ValueError):
    """A record is malformed or has an invalid relationship."""


def url_key(url: str) -> tuple[str, int | None, str, tuple[tuple[str, str], ...]]:
    """Validate a public HTTPS link and normalize it for duplicate detection."""
    if not isinstance(url, str) or re.search(r"[\s\\\x00-\x1f\x7f]", url):
        raise CatalogError(f"Invalid source URL: {url!r}")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError as exc:
        raise CatalogError(f"Invalid source URL: {url!r}") from exc
    labels = host.rstrip(".").split(".")
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or len(labels) < 2
        or labels[-1] in {"localhost", "local", "internal", "test", "invalid"}
        or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
    ):
        raise CatalogError(f"Expected a public HTTPS source URL: {url!r}")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise CatalogError(f"Use a publisher domain as the source URL: {url!r}")
    query = tuple(sorted(
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ))
    return host.rstrip(".").removeprefix("www."), None if port == 443 else port, parsed.path.rstrip("/"), query


def required_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{label} must be nonempty text")


def text_list(values: tuple[str, ...] | list[str], label: str, *, required: bool = False) -> None:
    if not isinstance(values, (tuple, list)) or (required and not values):
        raise CatalogError(f"{label} must be a list of text")
    for value in values:
        required_text(value, label)
    if len(set(values)) != len(values):
        raise CatalogError(f"{label} contains duplicate entries")


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    status: Status
    published_on: str | None = None
    reviewed_at: str | None = None
    review_note: str | None = None

    @property
    def publication_date(self) -> date | None:
        return date.fromisoformat(self.published_on) if self.published_on else None

    @property
    def verified_at(self) -> datetime | None:
        return (
            datetime.fromisoformat(self.reviewed_at)
            if self.status == "verified" and self.reviewed_at else None
        )

    def validate(self) -> None:
        required_text(self.title, f"{self.id} source title")
        url_key(self.url)
        if self.status not in STATUSES:
            raise CatalogError(f"{self.id} has an unknown evidence status")
        if self.review_note is not None:
            required_text(self.review_note, f"{self.id} review note")
        published = self.publication_date
        if self.published_on is not None and (
            published is None or published.isoformat() != self.published_on
        ):
            raise CatalogError(f"{self.id} needs an ISO publication date")
        if self.status == "verified" and not self.reviewed_at:
            raise CatalogError(f"{self.id} needs a review timestamp before verification")
        if self.reviewed_at is not None:
            reviewed = datetime.fromisoformat(self.reviewed_at)
            if reviewed.utcoffset() is None:
                raise CatalogError(f"{self.id} review timestamp needs a time zone")
            if reviewed > datetime.now(UTC):
                raise CatalogError(f"{self.id} has a future review timestamp")
            if self.status == "verified" and published and published > reviewed.date():
                raise CatalogError(f"{self.id} publication is later than verification")


@dataclass(frozen=True)
class Company:
    id: str
    name: str
    official_name: str
    website: str
    description: str
    segments: list[str]
    source_ids: list[str]

    def validate(self) -> None:
        required_text(self.name, f"{self.id} name")
        required_text(self.official_name, f"{self.id} official name")
        required_text(self.description, f"{self.id} description")
        url_key(self.website)
        text_list(self.segments, f"{self.id} segments")


@dataclass(frozen=True)
class Product:
    id: str
    company_id: str
    name: str
    category: str
    description: str
    source_ids: list[str]


@dataclass(frozen=True)
class Development:
    id: str
    source_id: str
    title: str
    company_ids: list[str]
    theme_ids: list[str]
    summary: str
    interpretation: str
    implication: str
    questions: list[str]
    limitations: str


def index_records[T: (Company, Product, Source, Development)](
    records: list[T], label: str
) -> dict[str, T]:
    index: dict[str, T] = {}
    for record in records:
        if not isinstance(record.id, str) or not SLUG.fullmatch(record.id):
            raise CatalogError(f"{label} ID must be a lowercase slug: {record.id!r}")
        if record.id in index:
            raise CatalogError(f"Duplicate {label} ID: {record.id}")
        index[record.id] = record
    return index


def require_links[T](ids: list[str], index: dict[str, T], label: str, *, required: bool = False) -> None:
    text_list(ids, label, required=required)
    for key in ids:
        if key not in index:
            raise CatalogError(f"{label} refers to unknown ID {key!r}")


@dataclass(frozen=True)
class MarketCatalog:
    companies: dict[str, Company]
    products: dict[str, Product]
    sources: dict[str, Source]
    developments: dict[str, Development]
    themes: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict) -> "MarketCatalog":
        try:
            catalog = cls(
                companies=index_records([Company(**item) for item in data["companies"]], "company"),
                products=index_records([Product(**item) for item in data["products"]], "product"),
                sources=index_records([Source(**item) for item in data["sources"]], "source"),
                developments=index_records(
                    [Development(**item) for item in data["developments"]], "development"
                ),
                themes=data["themes"],
            )
            catalog.validate()
        except CatalogError:
            raise
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            raise CatalogError(f"Invalid market catalog: {exc}") from exc
        return catalog

    def validate(self) -> None:
        source_urls = set()
        for source in self.sources.values():
            source.validate()
            normalized_url = url_key(source.url)
            if normalized_url in source_urls:
                raise CatalogError(f"Duplicate source URL: {source.url}")
            source_urls.add(normalized_url)

        if not isinstance(self.themes, dict):
            raise CatalogError("Themes must map IDs to display names")
        for key, theme in self.themes.items():
            if not isinstance(key, str) or not SLUG.fullmatch(key):
                raise CatalogError(f"Invalid theme ID: {key!r}")
            required_text(theme, f"{key} theme name")

        company_names = set()
        for company in self.companies.values():
            company.validate()
            name = company.name.strip().casefold()
            if name in company_names:
                raise CatalogError(f"Duplicate company name: {company.name}")
            company_names.add(name)
            require_links(company.source_ids, self.sources, f"{company.id} sources")

        product_names = set()
        for product in self.products.values():
            required_text(product.name, f"{product.id} name")
            required_text(product.category, f"{product.id} category")
            required_text(product.description, f"{product.id} description")
            require_links([product.company_id], self.companies, f"{product.id} company")
            require_links(product.source_ids, self.sources, f"{product.id} sources")
            name_key = (product.company_id, product.name.strip().casefold())
            if name_key in product_names:
                raise CatalogError(f"Duplicate product: {product.name}")
            product_names.add(name_key)

        used_sources = set()
        headlines = set()
        for item in self.developments.values():
            require_links(item.company_ids, self.companies, f"{item.id} companies", required=True)
            require_links(item.theme_ids, self.themes, f"{item.id} themes", required=True)
            require_links([item.source_id], self.sources, f"{item.id} original source")
            for value in (item.title, item.summary, item.interpretation, item.implication, item.limitations):
                required_text(value, f"{item.id} development text")
            text_list(item.questions, f"{item.id} research questions", required=True)
            source = self.sources[item.source_id]
            headline = (re.sub(r"[\W_]+", " ", item.title.casefold()).strip(), source.publication_date)
            if source.id in used_sources or headline in headlines:
                raise CatalogError(f"Duplicate development: {item.title}")
            if source.status == "verified" and source.publication_date is None:
                raise CatalogError(f"{item.id} needs a publication date for verified coverage")
            used_sources.add(source.id)
            headlines.add(headline)

    def evidence_status(self, source_ids: list[str]) -> Status:
        statuses = {self.sources[key].status for key in source_ids}
        if statuses == {"verified"}:
            return "verified"
        if statuses == {"unavailable"}:
            return "unavailable"
        return "unverified"

    def company_products(self, company_id: str) -> list[Product]:
        return [item for item in self.products.values() if item.company_id == company_id]

    def filter_developments(
        self,
        *,
        companies: set[str] | None = None,
        themes: set[str] | None = None,
        start: date | None = None,
        end: date | None = None,
        verified_only: bool = False,
    ) -> list[Development]:
        matches = []
        for item in self.developments.values():
            source = self.sources[item.source_id]
            published = source.publication_date
            if verified_only and source.status != "verified":
                continue
            if companies and not companies.intersection(item.company_ids):
                continue
            if themes and not themes.intersection(item.theme_ids):
                continue
            if start and (published is None or published < start):
                continue
            if end and (published is None or published > end):
                continue
            matches.append(item)
        return sorted(
            matches,
            key=lambda item: self.sources[item.source_id].publication_date or date.min,
            reverse=True,
        )

    def theme_coverage(self) -> dict[str, int]:
        counts = Counter(
            theme for item in self.filter_developments(verified_only=True) for theme in item.theme_ids
        )
        return {key: counts[key] for key in self.themes}


def load_catalog(path: Path = CATALOG_PATH) -> MarketCatalog:
    with path.open(encoding="utf-8") as file:
        return MarketCatalog.from_dict(json.load(file))
