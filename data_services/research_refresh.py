"""Validate a research snapshot and record manual source reviews."""

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from data_services.market_catalog import (
    CATALOG_PATH,
    STATUSES,
    CatalogError,
    MarketCatalog,
    Status,
    load_catalog,
)


def record_review(
    path: Path, source_id: str, status: Status, note: str, *, inspected: bool
) -> MarketCatalog:
    if status == "verified" and not inspected:
        raise CatalogError("Inspect the original content before setting a verified status")
    if not note.strip():
        raise CatalogError("Record what you checked, or why you could not complete the review")
    data = json.loads(path.read_text(encoding="utf-8"))
    catalog = MarketCatalog.from_dict(data)
    if source_id not in catalog.sources:
        raise CatalogError(f"Unknown source ID: {source_id}")

    source = next(row for row in data["sources"] if row["id"] == source_id)
    source.update(
        status=status,
        reviewed_at=datetime.now(UTC).isoformat(timespec="seconds"),
        review_note=note.strip(),
    )
    catalog = MarketCatalog.from_dict(data)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temp:
            temp_path = Path(temp.name)
            json.dump(data, temp, indent=2, ensure_ascii=False)
            temp.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Check record structure, dates, URLs and relationships")
    review = commands.add_parser("review", help="Record an analyst's manual source review")
    review.add_argument("source_id")
    review.add_argument("--status", choices=STATUSES, required=True)
    review.add_argument("--note", required=True)
    review.add_argument(
        "--inspected", action="store_true", help="Confirm you inspected the original source text"
    )
    args = parser.parse_args()
    try:
        if args.command == "validate":
            catalog = load_catalog(args.catalog)
        else:
            catalog = record_review(
                args.catalog, args.source_id, args.status, args.note, inspected=args.inspected
            )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

    print(
        f"Catalog valid. {len(catalog.companies)} companies, {len(catalog.products)} products, "
        f"{len(catalog.sources)} sources, "
        f"{len(catalog.filter_developments(verified_only=True))} verified developments."
    )


if __name__ == "__main__":
    main()
