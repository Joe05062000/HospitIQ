"""Evidence assembly, NVIDIA validation, and Streamlit workflow checks."""

import json
import unittest
from dataclasses import asdict
from email.message import Message
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from streamlit.testing.v1 import AppTest

from data_services.market_catalog import load_catalog
from data_services.nvidia_advisor import (
    ENDPOINT,
    MODEL,
    NvidiaError,
    NvidiaSettings,
    decode_priorities,
    load_settings,
    public_request,
    request_priorities,
)
from strategy_models.advisor import FINANCIAL_BRIEF_KEY, build_public_brief
from strategy_models.advisor_report import executive_html

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def reply(ids: list[str]) -> dict:
    return {
        "model": MODEL,
        "choices": [{
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps({"priorities": ids})},
        }],
    }


class AdvisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog()
        self.brief = build_public_brief(self.catalog, "growth", ("mews", "siteminder"), "independent", None)

    def test_local_brief_is_traceable_and_stays_in_scope(self) -> None:
        order = self.brief.priority_order()
        self.assertTrue(order[0].startswith("growth-"))
        self.assertEqual({item.section for item in self.brief.findings}, {"market", "growth", "competition", "investment", "cross-sell"})
        self.assertTrue(all(item.sources and all(src.status == "verified" for src in item.sources)
                            for item in self.brief.findings))
        filtered = build_public_brief(self.catalog, "market", ("mews",), "independent", "revenue")
        self.assertFalse(any(item.section == "competition" for item in filtered.findings))
        self.assertFalse(any(item.section == "market" for item in filtered.findings))
        export = executive_html(self.catalog, self.brief, order, "Evidence-Based Mode", None)
        self.assertIn("Decision agenda", export)
        self.assertIn(self.brief.findings[next(index for index, item in enumerate(self.brief.findings) if item.id == order[0])].sources[0].url, export)

    def test_configuration_accepts_alias_and_never_repr_displays_key(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.toml"
            path.write_text('NVIDIA_API_KEY = "test-only-key"\nNVIDIA_MODEL = "nemotron-3-ultra-550b-a55b"\n')
            settings = load_settings(path)
            self.assertEqual(settings.model, MODEL)
            self.assertNotIn("test-only-key", repr(settings))
            path.write_text('NVIDIA_API_KEY = "test-only-key"\nNVIDIA_MODEL = "different-model"\n')
            with self.assertRaisesRegex(NvidiaError, "Ultra 550B"):
                load_settings(path)

    def test_response_schema_rejects_hallucinated_duplicate_and_foreign_model_ids(self) -> None:
        key = self.brief.priority_order()[0]
        self.assertEqual(decode_priorities(reply([key]), self.brief), (key,))
        for body in (
            reply(["invented-id"]), reply([key, key]), reply([]),
            reply([key]) | {"model": "another-model"}, {},
        ):
            with self.subTest(response=body), self.assertRaises(NvidiaError):
                decode_priorities(body, self.brief)

    def test_transport_uses_only_fixed_model_endpoint_and_public_payload(self) -> None:
        key = self.brief.priority_order()[0]
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(reply([key])).encode()
        with patch("data_services.nvidia_advisor.trial_enabled", return_value=True), patch("data_services.nvidia_advisor.build_opener", return_value=opener):
            result = request_priorities(self.brief, NvidiaSettings("test-only-key"))
        called = opener.open.call_args.args[0]
        self.assertEqual(result, (key,))
        self.assertEqual(called.full_url, ENDPOINT)
        self.assertEqual(json.loads(called.data), public_request(self.brief))
        self.assertNotIn("test-only-key", called.data.decode())
        self.assertNotIn("financial", asdict(self.brief))


    def test_provider_quota_fails_once_without_retry(self) -> None:
        opener = MagicMock()
        opener.open.side_effect = HTTPError(ENDPOINT, 429, "Sensitive upstream content", Message(), None)
        with patch("data_services.nvidia_advisor.trial_enabled", return_value=True), patch("data_services.nvidia_advisor.build_opener", return_value=opener), self.assertRaisesRegex(
            NvidiaError, r"HTTP 429"
        ) as error:
            request_priorities(self.brief, NvidiaSettings("test-only-key"))
        self.assertNotIn("Sensitive upstream content", str(error.exception))
        opener.open.assert_called_once()


class AdvisorPageTests(unittest.TestCase):
    def open_advisor(self) -> AppTest:
        return AppTest.from_file(APP, default_timeout=10).run().switch_page("app_pages/ai_strategy_advisor.py").run()

    def test_offline_default_and_nvidia_failure_fallback(self) -> None:
        with patch("data_services.nvidia_advisor.trial_enabled", return_value=True), patch(
            "data_services.nvidia_advisor.request_priorities", side_effect=NvidiaError("Test unavailable")
        ) as mock:
            app = self.open_advisor()
            self.assertFalse(app.exception)
            mock.assert_not_called()
            app.radio(key="advisor_mode").set_value("NVIDIA-assisted").run()
            mock.assert_not_called()
            with patch("data_services.nvidia_advisor.load_settings", return_value=NvidiaSettings("test-only")):
                app.button(key="advisor_nvidia_run").click().run()
            mock.assert_called_once()
        self.assertFalse(app.exception)
        self.assertTrue(any("local Evidence-Based" in item.value for item in app.warning))
        self.assertEqual(app.get("download_button")[0].proto.label, "Download executive strategy brief")

    def test_investment_question_explains_handoff_before_showing_limits(self) -> None:
        app = self.open_advisor()
        app.selectbox(key="advisor_question").select("investment").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.number_input)
        self.assertTrue(any("Executive brief → Open results in Strategy Advisor" in item.value for item in app.markdown))
        self.assertIn("Open Financial Scenario Simulator", [link.proto.label for link in app.get("page_link")])

    def test_financial_handoff_remains_local_and_preserves_modeled_totals(self) -> None:
        app = AppTest.from_file(APP, default_timeout=10).run().switch_page(
            "app_pages/financial_scenario_simulator.py"
        ).run()
        app.selectbox(key="financial_product").select("sm-booking").run()
        app.selectbox(key="financial_segment").select("resort").run()
        app.selectbox(key="financial_sm-booking:resort_Base_demo_activation").select("Beginning of year").run()
        app.button(key="financial_share_advisor").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Strategy Advisor")
        self.assertEqual(app.selectbox(key="advisor_question").value, "investment")
        self.assertEqual(app.multiselect(key="advisor_companies").value, ["siteminder"])
        self.assertEqual(app.selectbox(key="advisor_segment").value, "resort")
        snapshot = app.session_state[FINANCIAL_BRIEF_KEY]
        self.assertEqual(snapshot.product_id, "sm-booking")
        self.assertTrue(any("1,029,475" in item.value for item in app.markdown))
