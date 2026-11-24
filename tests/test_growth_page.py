"""Streamlit smoke coverage for public and session-only growth workflows."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def open_growth() -> AppTest:
    return AppTest.from_file(APP).run().switch_page("app_pages/product_growth_intelligence.py").run()


class GrowthPageTests(unittest.TestCase):
    def test_public_workflow_and_filters(self) -> None:
        app = open_growth()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Product Growth Intelligence")
        self.assertEqual(len(app.tabs), 5)
        self.assertTrue(any("Documented product-pair integration" in item.value for item in app.markdown))
        self.assertEqual(app.get("download_button")[0].proto.label, "Download 90-day playbook")
        app.multiselect(key="growth_product_filter_mews").set_value([]).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("download_button"))

    def test_upload_is_processed_without_storing_rows_in_app_session_state(self) -> None:
        uploaded = Mock()
        uploaded.getvalue.return_value = (
            b"customer_id,existing_products,eligible_products,organization_segment\n"
            b"unique-upload-private-id,mews-pms,mews-pay,independent\n"
        )
        with patch("ui.growth.private_demo", return_value=True), patch("streamlit.file_uploader", return_value=uploaded):
            app = open_growth()
            app.radio(key="growth_mode").set_value("Customer Portfolio Mode").run()
        self.assertFalse(app.exception)
        self.assertIn("Validated 1 customer rows.", app.success[0].value)
        self.assertTrue(any("Pilot candidate" in item.value for item in app.markdown))
        self.assertNotIn("unique-upload-private-id", repr(app.session_state))
        app.radio(key="growth_mode").set_value("Public Research Mode").run()
        self.assertFalse(app.exception)
        self.assertFalse(any("unique-upload-private-id" in item.value for item in app.text))

    def test_synthetic_mode_is_explicit(self) -> None:
        app = open_growth()
        app.radio(key="growth_mode").set_value("Customer Portfolio Mode").run()
        app.radio(key="growth_input_kind").set_value("Synthetic demonstration").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Four fictional Mews scenarios" in item.value for item in app.caption))
