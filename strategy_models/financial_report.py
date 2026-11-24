"""Executive HTML export generated from validated scenario projections."""

from collections.abc import Mapping, Sequence
from html import escape

from brand import PRODUCT_DESCRIPTOR, PRODUCT_NAME
from data_services.market_catalog import MarketCatalog
from strategy_models.financial import (
    FORMULAS,
    LIMITATIONS,
    METHODOLOGY,
    Projection,
    Sensitivity,
    payback_label,
)
from strategy_models.financial_transfer import Opportunity
from strategy_models.growth_playbook import segment_label
from strategy_models.growth_research import CATEGORY_LABELS


def money(value: float, currency: str) -> str:
    amount = f"{abs(value):,.0f}"
    return f"{'−' if value < 0 else ''}{currency} {amount}"


ROUNDED_COUNTS = "Displayed customer counts are rounded expectations. Financial calculations use unrounded estimates."


def rollout_payback(result: Projection) -> str:
    return f"{payback_label(result)} · Year {result.assumptions.rollout_year} launch"


def assumption_lines(result: Projection, currency: str) -> tuple[tuple[str, str], ...]:
    inputs = result.assumptions
    return (
        ("Eligible non-adopters", f"{inputs.eligible:,}"),
        ("Applied adoption, Years 1–3", " / ".join(f"{rate:.1%}" if rate is not None else "Pre-launch" for rate in inputs.active_adoption)),
        ("Operating years", f"Year {inputs.rollout_year}–3" if inputs.rollout_year < 3 else "Year 3"),
        ("Customer activation timing", inputs.activation),
        ("Annual revenue per adopter", money(inputs.revenue_per_adopter, currency)),
        ("Contribution margin", f"{inputs.margin:.1%}"),
        ("Annual fixed costs", money(inputs.fixed_cost, currency)),
        ("One-time investment", money(inputs.investment, currency)),
        ("Rollout year", str(inputs.rollout_year)),
        ("Annual retention", f"{inputs.retention:.1%}"),
    )


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    header = "".join(f'<th scope="col">{escape(value)}</th>' for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>'


def annual_rows(result: Projection, currency: str) -> list[tuple[str, str, str, str]]:
    fields = (
        ("New adopters", "new_adopters"), ("Retained adopters", "retained_adopters"),
        ("Churned adopters", "churned_adopters"), ("Active adopters", "active_adopters"),
        ("Remaining eligible non-adopters", "remaining"),
        ("Incremental revenue", "revenue"), ("Variable costs", "variable_cost"),
        ("Contribution profit", "contribution_profit"), ("Recurring fixed costs", "fixed_cost"),
        ("Estimated operating contribution", "operating_contribution"), ("One-time investment", "investment"),
        ("Net cash contribution", "cash_contribution"), ("Cumulative net cash contribution", "cumulative_cash"),
    )
    rows = []
    for index, (label, field) in enumerate(fields):
        values = [getattr(year, field) for year in result.years]
        formatted = [f"{value:,.0f}" if index < 5 else money(value, currency) for value in values]
        rows.append((label, formatted[0], formatted[1], formatted[2]))
    return rows


def briefing_html(
    catalog: MarketCatalog, opportunity: Opportunity, results: Mapping[str, Projection],
    focus: str, sensitivities: tuple[Sensitivity, ...], currency: str, assumption_origin: str, step: float,
    *, uncertainty: tuple[Sensitivity, ...] = (), ranges: Mapping[str, tuple[float, float]] | None = None,
    aligned: Mapping[str, Projection] | None = None,
) -> str:
    product = catalog.products[opportunity.product_id]
    product_label = opportunity.fictional_label or product.name
    chosen = results[focus]
    scenario_rows = [
        (
            name, *(money(year.revenue, currency) for year in projection.years),
            *(money(year.operating_contribution, currency) for year in projection.years),
            money(projection.ending_cash, currency), rollout_payback(projection),
        )
        for name, projection in results.items()
    ]
    scenario_assumptions = "".join(
        f"<h3>{escape(name)}</h3>" + table(("Assumption", "Value"), assumption_lines(result, currency))
        for name, result in results.items()
    )
    sources = []
    for key in opportunity.source_ids:
        if (source := catalog.sources.get(key)) and source.status == "verified":
            sources.append(f'<li><a href="{escape(source.url, quote=True)}">{escape(source.title)}</a></li>')
    known = (
        f"{opportunity.known_eligible:,} known eligible non-adopters with unique IDs in the supplied input."
        if opportunity.known_eligible is not None else "A confirmed eligible population was unavailable."
    )
    sensitive_rows = [
        (item.driver, money(item.low_change, currency), money(item.high_change, currency))
        for item in sensitivities
    ]
    uncertainty_html = ""
    if uncertainty and ranges:
        assumed = [(item.driver, f"{ranges[item.driver][0]:+.0%} to {ranges[item.driver][1]:+.0%}",
                    money(item.low_change, currency), money(item.high_change, currency)) for item in uncertainty]
        uncertainty_html = (
            "<h2>Business uncertainty</h2><p>Explicitly assumed ranges. Practical risk also depends "
            "on uncertainty and controllability.</p>"
            + table(("Driver", "Relative range", "Lower input cash change", "Higher input cash change"), assumed)
        )
    aligned_html = ""
    if aligned:
        common_year = next(iter(aligned.values())).assumptions.rollout_year
        aligned_html = f"<h3>Common Year {common_year} launch</h3>" + table(
            ("Scenario", "Three-year cash"), [(name, money(item.ending_cash, currency)) for name, item in aligned.items()]
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive financial briefing · {escape(PRODUCT_NAME)}</title>
<style>
body {{ margin: 2rem auto; max-width: 70rem; padding: 0 1rem; color: #17324d; font: 16px/1.5 system-ui; }}
a {{ color: #176f9b; }} table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
th, td {{ text-align: left; padding: .5rem; border-bottom: 1px solid #dce7ef; }}
th {{ background: #e3f4fb; }} .table-wrap {{ overflow-x: auto; }}
@media print {{ body {{ font-size: 10pt; }} table {{ font-size: 8pt; }} }}
</style></head>
<body><main><p><strong>{escape(PRODUCT_NAME)}</strong> · {escape(PRODUCT_DESCRIPTOR)}</p><h1>Executive financial briefing</h1>
<p><strong>{escape(product_label)}</strong> · {escape(CATEGORY_LABELS[opportunity.category])}
· {escape(segment_label(opportunity.segment))}</p>
<p>{escape("Fictional product assumptions. The cited vendor product provides industry context." if opportunity.fictional_label else product.description)}</p>
<p><strong>Eligibility</strong> · {escape(opportunity.eligibility_status)}</p>
<p>{escape(known)} {escape(assumption_origin)}</p>
<h2>{escape(focus)} scenario · Three-year financial impact</h2>
{table(("Measure", "Year 1", "Year 2", "Year 3"), annual_rows(chosen, currency))}
<p>{escape(ROUNDED_COUNTS)}</p>
<p>Approximate payback from rollout: {escape(rollout_payback(chosen))}</p>
<h2>Scenario comparison</h2>
{table(("Scenario", "Y1 revenue", "Y2 revenue", "Y3 revenue", "Y1 op. contribution", "Y2 op. contribution",
"Y3 op. contribution", "3-year cash", "Approximate payback from rollout"), scenario_rows)}
{aligned_html}<h2>Financial assumptions</h2>{scenario_assumptions}
<h2>Normalized sensitivity</h2>
<p>Three-year cash change relative to the selected scenario. All inputs move by ±{step:.0%} relative to the selected scenario (rates capped at 100%). Inputs are moved one at a time.</p>
{table(("Driver", "Lower input", "Higher input"), sensitive_rows)}
<p>These stress tests describe the model's response to input changes. They do not estimate statistical confidence.</p>
{uncertainty_html}<h2>Risks and validation</h2>
<ol><li>Confirm product ownership and unique eligible accounts. Validate local availability, procurement, and compatibility.</li>
<li>Test adoption timing, retention, incremental price, and willingness to pay in a qualified pilot.</li>
<li>Verify delivery, support, and implementation costs with operations and finance.</li></ol>
<p><strong>Decision checkpoints</strong> Qualify the population before pilot spend. Review observed adoption
and unit economics before expansion. Revisit funding if the downside case exceeds risk tolerance.</p>
<h2>Methodology and scope</h2>
<p>{escape(METHODOLOGY)}</p><p>{escape(FORMULAS)}</p><p>{escape(LIMITATIONS)}</p>
<h2>Public product evidence</h2><ul>{"".join(sources)}</ul>
</main></body></html>"""
