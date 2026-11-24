"""Printable case study briefing from reviewed evidence and model results."""

from html import escape

from brand import CASE_STUDY_TITLE, PRODUCT_DESCRIPTOR, PRODUCT_NAME
from data_services.market_catalog import MarketCatalog
from strategy_models.executive_case import (
    BUSINESS_RANGES,
    CASE_LIMIT,
    COMPANY,
    CONSERVATIVE_TIMING,
    CURRENCY,
    CUSTOMER_BASE,
    MILESTONES,
    ORIGIN,
    POPULATION,
    QUESTION,
    RECOMMENDATION,
    RISK_CONTEXT,
    RISKS,
    STRESS,
    ExecutiveCase,
    sensitivity_takeaways,
)
from strategy_models.financial import FORMULAS, LIMITATIONS, METHODOLOGY
from strategy_models.financial_report import (
    assumption_lines,
    money,
    rollout_payback,
    table,
)


def scenario_rows(case: ExecutiveCase) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (name, *(money(year.revenue, CURRENCY) for year in result.years),
         money(result.total_operating, CURRENCY), money(result.ending_cash, CURRENCY), rollout_payback(result))
        for name, result in case.results.items()
    )


SCENARIO_HEADERS = (
    "Scenario", "Year 1 revenue", "Year 2 revenue", "Year 3 revenue",
    "Three-year operating contribution", "Three-year net cash", "Approximate payback from rollout",
)


def case_report(catalog: MarketCatalog, case: ExecutiveCase) -> str:
    normalized, uncertainty = sensitivity_takeaways(case)
    base = case.results["Base"]
    sources = {}
    market_notes = []
    for item in case.developments:
        market_notes.append(f"<li><strong>{escape(item.title)}</strong> {escape(item.summary)}</li>")
        sources[item.source_id] = catalog.sources[item.source_id]
    contrasts = []
    for vendor, entries in case.payments_evidence:
        for entry in entries:
            contrasts.append(f"<li><strong>{escape(vendor)}</strong> {escape(entry.text)}</li>")
            sources.update((source.id, source) for source in entry.sources)
    source_links = "".join(
        f'<li><a href="{escape(source.url, quote=True)}">{escape(source.title)}</a></li>'
        for source in sources.values()
    )
    step_rows = tuple((item.driver, money(item.low_change, CURRENCY), money(item.high_change, CURRENCY))
                      for item in case.sensitivities)
    uncertain_rows = tuple(
        (item.driver, f"{BUSINESS_RANGES[item.driver][0]:+.0%} to {BUSINESS_RANGES[item.driver][1]:+.0%}",
         money(item.low_change, CURRENCY), money(item.high_change, CURRENCY))
        for item in case.uncertainty
    )
    aligned_rows = tuple((name, money(result.ending_cash, CURRENCY)) for name, result in case.aligned.items())
    assumptions = "".join(f"<h3>{escape(name)}</h3>" + table(("Assumption", "Value"), assumption_lines(result, CURRENCY))
                          for name, result in case.results.items())
    pilot = "".join(
        f"<li><strong>{escape(title)}</strong> {escape(action)}</li>"
        for title, action, _ in MILESTONES
    )
    gates = "".join(f"<li>{escape(gate)}</li>" for _, _, gate in MILESTONES)
    growth = case.complementarity
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(CASE_STUDY_TITLE)} · {escape(PRODUCT_NAME)}</title>
<style>
body {{ max-width: 68rem; margin: 2rem auto; padding: 0 1rem; color: #17324d; font: 16px/1.55 system-ui; }}
header {{ background: #176f9b; color: white; padding: 1rem 1.5rem; border-radius: .65rem; }}
header h1 {{ margin: .25rem 0; }} a {{ color:#176f9b; overflow-wrap:anywhere; }}
table {{ border-collapse:collapse; width:100%; }} th,td {{ padding:.5rem; text-align:left; border-bottom:1px solid #dce7ef; }}
th {{ background:#e3f4fb; }} .table-wrap {{ overflow-x:auto; }}
@media(max-width:640px) {{ body {{ margin:1rem auto; }} th,td {{ font-size:.85rem; }} }}
@media print {{ body {{ margin:0; font-size:10pt; }} th,td {{ font-size:8pt; }} }}
</style></head><body><main>
<header><p><strong>{escape(PRODUCT_NAME)}</strong> · {escape(PRODUCT_DESCRIPTOR)}</p><h1>{escape(CASE_STUDY_TITLE)}</h1><p>{escape(COMPANY)} · Fictional company</p></header>
<h2>Decision required</h2>
<p>{escape(QUESTION)} The fictional portfolio has {CUSTOMER_BASE:,} existing hotel customers and assumes
{POPULATION:,} distinct eligible non-adopters for payments.</p>
<h2>Executive recommendation</h2><p>{escape(RECOMMENDATION)}</p>
<h2>Supporting market evidence</h2><ul>{"".join(market_notes) or "<li>No matching reviewed announcements.</li>"}</ul>
<h3>Competitive findings</h3><ul>{"".join(contrasts) or "<li>Insufficient verified comparison evidence.</li>"}</ul>
<p>These sources describe vendor product scope. They provide industry context for fictional Harborlight.</p>
<p><strong>Opportunity to test</strong> {escape(growth.rationale if growth else "Validate payments workflows and buyer need.")}
{escape(growth.execution if growth else "")}</p>
<h2>Financial outcomes</h2>
<p>{escape(ORIGIN)} Base three-year revenue is {money(base.total_revenue, CURRENCY)}. Payback is approximate and measured from rollout.</p>
{table(SCENARIO_HEADERS, scenario_rows(case))}
<p>{escape(CASE_LIMIT)}</p><p>{escape(CONSERVATIVE_TIMING)}</p>
<h3>Year 1 launch comparison</h3>
<p>The Conservative case uses a separately assumed 12% Year 1 adoption rate in this comparison.
The delayed version excludes Year 1 cash and operations.</p>
{table(("Case", "Three-year cash with Year 1 launch"), aligned_rows)}
<h2>Key risks and sensitivities</h2>
<h3>Normalized sensitivity analysis</h3>
<p>{escape(normalized)} Each driver moves by ±{STRESS:.0%} relative. Values are changes in three-year Base cash.</p>
{table(("Driver", "Lower input", "Higher input"), step_rows)}
<h3>Assumed business uncertainty</h3><p>{escape(uncertainty)} {escape(RISK_CONTEXT)}</p>
{table(("Driver", "Assumed range", "Lower input", "Higher input"), uncertain_rows)}
<ul>{"".join(f"<li>{escape(risk)}</li>" for risk in RISKS)}</ul>
<h2>Proposed 90-day pilot</h2><ol>{pilot}</ol>
<h2>Decision gates</h2><ol>{gates}</ol>
<h2>Sources and assumptions</h2>
<h3>Public sources</h3><ul>{source_links}</ul>
<h3>Assumptions and methodology</h3>{assumptions}
<p>{escape(METHODOLOGY)}</p><p>{escape(FORMULAS)}</p><p>{escape(LIMITATIONS)}</p>
</main></body></html>"""
