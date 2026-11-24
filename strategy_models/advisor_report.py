"""Local, source-linked executive brief export."""

from html import escape

from brand import PRODUCT_DESCRIPTOR, PRODUCT_NAME
from data_services.market_catalog import MarketCatalog
from strategy_models.advisor import (
    QUESTIONS,
    SECTION_NAMES,
    FinancialSnapshot,
    PublicBrief,
)
from strategy_models.financial import LIMITATIONS
from strategy_models.financial_report import money, rollout_payback, table
from strategy_models.growth_engine import ATTRACTIVENESS_QUALIFIER

EVIDENCE_LIMITS = (
    "This brief draws from the reviewed first-party catalog. Product documentation supports stated "
    "capabilities and announcements describe public plans. Strategic interpretations and segment needs "
    "remain hypotheses. Current availability, customer adoption, pricing, and outcomes may require direct validation."
)


def financial_rows(snapshot: FinancialSnapshot) -> list[tuple[str, ...]]:
    return [
        (
            name, *(money(year.revenue, snapshot.currency) for year in result.years),
            money(result.total_operating, snapshot.currency), money(result.ending_cash, snapshot.currency),
            rollout_payback(result),
        )
        for name, result in snapshot.scenarios
    ]


FINANCIAL_HEADERS = (
    "Case", "Year 1 revenue", "Year 2 revenue", "Year 3 revenue",
    "Operating contribution", "Three-year net cash", "Approximate payback from rollout",
)


def executive_html(
    catalog: MarketCatalog, brief: PublicBrief, priorities: tuple[str, ...], mode: str,
    financial: FinancialSnapshot | None,
) -> str:
    items = {item.id: item for item in brief.findings}
    top = "".join(f"<li><strong>{escape(items[key].title)}</strong> · {escape(brief.segment)}. {escape(items[key].interpretation)} Validate {escape(items[key].metric)}. Next: {escape(items[key].action)}</li>" for key in priorities)
    findings = []
    for section, label in SECTION_NAMES.items():
        if section != brief.focus_section():
            continue
        findings.append(f"<h2>{escape(label)}</h2>")
        for item in (item for item in brief.findings if item.section == section):
            links = " · ".join(
                f'<a href="{escape(source.url, quote=True)}">{escape(source.title)}</a>'
                for source in item.sources
            )
            findings.append(
                f"<h3>{escape(item.title)}</h3><p><strong>Evidence</strong> {escape(item.evidence)}</p>"
                f"<p><strong>Interpretation</strong> {escape(item.interpretation)}</p>"
                + (f"<p><strong>Assumptions and limits</strong> {escape(item.assumption)}</p>" if item.assumption else "")
                +
                f"<p><strong>Next step</strong> {escape(item.action)}</p><p>{links}</p>"
            )
    finance = "<p>No matching simulator results were included.</p>"
    if financial is not None:
        product = catalog.products[financial.product_id]
        segment = "Segment unspecified" if financial.segment is None else brief.segment
        finance = (
            f"<p>{escape(financial.fictional_label or product.name)} · {escape(segment)} · {escape(financial.origin)}</p>"
            + table(FINANCIAL_HEADERS, financial_rows(financial))
            + f"<p>{escape(LIMITATIONS)}</p>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive strategy brief · {escape(PRODUCT_NAME)}</title><style>
body {{ max-width: 65rem; margin: 2rem auto; padding: 0 1rem; color: #17324d; font: 16px/1.5 system-ui; }}
a {{ color: #176f9b; overflow-wrap: anywhere; }} table {{ border-collapse: collapse; }}
th, td {{ padding: .5rem; text-align: left; border-bottom: 1px solid #dce7ef; }}
th {{ background: #e3f4fb; }} .table-wrap {{ overflow-x: auto; }}
</style></head><body><main><p><strong>{escape(PRODUCT_NAME)}</strong> · {escape(PRODUCT_DESCRIPTOR)}</p>
<h1>Executive strategy brief</h1>
<p>{escape(QUESTIONS[brief.question])}</p>
<p>{escape(", ".join(brief.companies))} · {escape(brief.segment)} · {escape(mode)}</p>
<p>Market theme: {escape(brief.theme or "All verified themes")}</p>
<h2>Decision agenda</h2>
{f"<p>{escape(ATTRACTIVENESS_QUALIFIER)}</p>" if brief.question == "growth" else ""}<ol>{top}</ol>
{"".join(findings)}
<h2>Local financial scenario results</h2>{finance}
<h2>Evidence limitations</h2><p>{escape(EVIDENCE_LIMITS)}</p>
</main></body></html>"""
