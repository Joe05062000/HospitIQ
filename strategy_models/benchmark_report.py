"""Portable executive comparison report and accessible capability table."""

from html import escape
from pathlib import Path

from brand import PRODUCT_DESCRIPTOR, PRODUCT_NAME
from data_services.market_catalog import Source
from strategy_models.benchmark import CATEGORIES, Benchmark, Cell

LIMITATIONS = (
    "Coverage reflects the reviewed catalog. An evidence gap leaves the capability unverified. "
    "Features, rollout status, commercial terms, adoption and performance can differ by market "
    "or deployment. Shared capability categories do not establish feature parity."
)
MATRIX_STYLE = Path(__file__).resolve().parents[1] / "ui" / "assets" / "matrix.css"


def source_anchor(source: Source) -> str:
    return f'<a href="{escape(source.url, quote=True)}">{escape(source.title)}</a>'


def cell_html(cell: Cell) -> str:
    status_class = {
        "Documented capability": "documented",
        "Not verified in current research": "unverified",
        "Not applicable": "excluded",
        "Announced or limited availability": "unverified",
    }[cell.status]
    parts = [f'<span class="matrix-status {status_class}">{escape(cell.status)}</span>']
    if cell.evidence:
        parts.append("<ul>")
        for item in cell.evidence:
            links = " · ".join(source_anchor(source) for source in item.sources)
            stage = f"<strong>{escape(item.stage)}</strong> · " if item.stage else ""
            parts.append(f"<li>{stage}{escape(item.text)}<small>{links}</small></li>")
        parts.append("</ul>")
    return "".join(parts)


def matrix_html(benchmark: Benchmark) -> str:
    names = {key: escape(benchmark.catalog.companies[key].name) for key in benchmark.companies}
    headers = "".join(f'<th scope="col">{name}</th>' for name in names.values())
    rows = []
    for category, cells in benchmark.matrix.items():
        values = "".join(
            f'<td><span class="matrix-mobile-label">{names[key]}</span>{cell_html(cells[key])}</td>'
            for key in benchmark.companies
        )
        rows.append(f'<tr><th scope="row">{escape(CATEGORIES[category])}</th>{values}</tr>')
    return (
        '<table class="capability-matrix" aria-label="Documented product capability comparison">'
        f'<thead><tr><th scope="col">Capability</th>{headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def executive_report(benchmark: Benchmark) -> str:
    company_names = ", ".join(benchmark.catalog.companies[key].name for key in benchmark.companies)
    similarities = ", ".join(CATEGORIES[key] for key in benchmark.similarities)
    sources: dict[str, Source] = {}
    rows = []
    for contrast in benchmark.contrasts:
        observations = "".join(
            f"<li>{escape(item.text)} · {' · '.join(map(source_anchor, item.sources))}</li>"
            for index in range(len(contrast.companies))
            for item in benchmark.contrast_evidence(contrast, index)
        )
        rows.append(
            f"<h3>{escape(contrast.title)}</h3><ul>{observations}</ul>"
            f"<p><strong>Strategic interpretation</strong> {escape(contrast.significance)}</p>"
            f"<p><strong>Investment implication</strong> {escape(contrast.investment)}</p>"
            f"<p><strong>Portfolio opportunity</strong> {escape(contrast.expansion)}</p>"
            f"<p><strong>Due diligence</strong> {escape(contrast.question)}</p>"
        )
    portfolios = []
    for company_id in benchmark.companies:
        company = benchmark.catalog.companies[company_id]
        products = [
            product for product in benchmark.catalog.company_products(company_id)
            if benchmark.catalog.evidence_status(product.source_ids) == "verified"
        ]
        listed = []
        for product in products:
            refs = [benchmark.catalog.sources[key] for key in product.source_ids]
            sources.update((source.id, source) for source in refs)
            listed.append(
                f"<li>{escape(product.name)} · {' · '.join(map(source_anchor, refs))}</li>"
            )
        portfolios.append(
            f"<h3>{escape(company.name)}</h3>"
            + (f"<ul>{''.join(listed)}</ul>" if listed else "<p>No verified portfolio products recorded.</p>")
        )
    for row in benchmark.matrix.values():
        for cell in row.values():
            for item in cell.evidence:
                sources.update((source.id, source) for source in item.sources)
    source_list = "".join(
        f"<li>{source_anchor(source)}</li>"
        for source in sorted(sources.values(), key=lambda item: item.title.casefold())
    )
    differences = "".join(rows) or "<p>No curated contrast has sufficient verified evidence.</p>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive comparison · {escape(PRODUCT_NAME)}</title>
<style>
body {{ margin: 2rem auto; max-width: 76rem; padding: 0 1rem; color: #17324D;
font: 16px/1.5 system-ui, sans-serif; }}
a {{ color: #176F9B; overflow-wrap: anywhere; }}
{MATRIX_STYLE.read_text(encoding="utf-8")}
</style></head><body><main><p><strong>{escape(PRODUCT_NAME)}</strong> · {escape(PRODUCT_DESCRIPTOR)}</p>
<h1>Executive comparison</h1><p>{escape(company_names)}</p>
<h2>Documented similarities</h2><p>{escape(similarities or "No shared category verified across the full selection.")}</p>
<h2>Documented differences and strategic implications</h2>{differences}
<h2>Evidence limitations</h2><p>{escape(LIMITATIONS)}</p>
<h2>Documented product portfolios</h2>{"".join(portfolios)}
<h2>Capability matrix</h2>{matrix_html(benchmark)}
<h2>Source references</h2><ol>{source_list}</ol>
</main></body></html>"""
