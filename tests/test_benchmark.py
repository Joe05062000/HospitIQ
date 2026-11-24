"""Evidence, selection, comparison, theme and export regression checks."""

import unittest
from dataclasses import replace

from data_services.market_catalog import load_catalog
from strategy_models.benchmark import (
    CATEGORIES,
    THEMES,
    Evidence,
    build_benchmark,
    classify,
    eligible_companies,
    theme_companies,
    theme_developments,
)
from strategy_models.benchmark_report import executive_report, matrix_html


class BenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog()

    def test_company_selection(self) -> None:
        keys = eligible_companies(self.catalog)
        self.assertEqual(keys, ("oracle", "mews", "amadeus", "siteminder"))
        for selection in ((), ("oracle",), ("oracle", "oracle"), ("oracle", "unknown"), keys + ("other",)):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                build_benchmark(self.catalog, selection)
        self.assertEqual(build_benchmark(self.catalog, ("mews", "oracle")).companies, ("mews", "oracle"))

    def test_matrix_missing_evidence_and_traceability(self) -> None:
        benchmark = build_benchmark(self.catalog, ("oracle", "amadeus"))
        self.assertEqual(tuple(benchmark.matrix), tuple(CATEGORIES))
        oracle = benchmark.matrix["pms"]["oracle"]
        amadeus = benchmark.matrix["pms"]["amadeus"]
        self.assertEqual(oracle.status, "Documented capability")
        self.assertEqual(amadeus.status, "Not verified in current research")
        self.assertEqual(amadeus.evidence, ())
        self.assertIn("oracle-hotels", {source.id for item in oracle.evidence for source in item.sources})

        for row in benchmark.matrix.values():
            for cell in row.values():
                for item in cell.evidence:
                    self.assertTrue(item.sources)
                    for source in item.sources:
                        self.assertEqual(source, self.catalog.sources[source.id])
                        self.assertEqual(source.status, "verified")
        self.assertNotIn("Not applicable", {cell.status for row in benchmark.matrix.values() for cell in row.values()})

    def test_status_classification_and_source_downgrade(self) -> None:
        reviewed_scope = Evidence("An explicit scope exclusion", (self.catalog.sources["oracle-hotels"],))
        self.assertEqual(classify(()).status, "Not verified in current research")
        self.assertEqual(classify((), (reviewed_scope,)).status, "Not applicable")
        self.catalog.sources["oracle-assistant"] = replace(
            self.catalog.sources["oracle-assistant"], status="unavailable"
        )
        benchmark = build_benchmark(self.catalog, ("oracle", "mews"))
        self.assertEqual(benchmark.matrix["ai"]["oracle"].status, "Not verified in current research")
        self.assertEqual(benchmark.contrasts, ())

    def test_curated_comparisons_and_theme_filter(self) -> None:
        benchmark = build_benchmark(self.catalog, ("mews", "siteminder"))
        self.assertIn("distribution", benchmark.similarities)
        self.assertEqual(len(benchmark.contrasts), 1)
        contrast = benchmark.contrasts[0]
        self.assertEqual(contrast.companies, ("mews", "siteminder"))
        self.assertIn("mews-siteminder", {
            source.id for item in benchmark.contrast_evidence(contrast, 1) for source in item.sources
        })
        theme = next(item for item in THEMES if item.name == "Hotel distribution")
        self.assertEqual(theme_companies(benchmark, theme), ("mews", "siteminder"))
        self.assertEqual([item.id for item in theme_developments(benchmark, theme)],
                         ["siteminder-commerce", "mews-siteminder"])
        analytics = next(item for item in THEMES if item.name == "Analytics")
        self.assertEqual(theme_developments(benchmark, analytics), [])

    def test_report_escapes_text_and_preserves_sources(self) -> None:
        self.catalog.companies["oracle"] = replace(self.catalog.companies["oracle"], name="Oracle <Hotels>")
        benchmark = build_benchmark(self.catalog, ("oracle", "mews"))
        html = executive_report(benchmark)
        self.assertIn("Oracle &lt;Hotels&gt;", html)
        self.assertIn('scope="col">Mews', matrix_html(benchmark))
        self.assertIn("Evidence limitations", html)
        self.assertIn("Documented product portfolios", html)
        self.assertIn("Front-desk assistance and finance automation", html)
        self.assertIn(self.catalog.sources["oracle-assistant"].url, html)
        self.assertIn('name="viewport"', html)
