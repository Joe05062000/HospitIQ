"""Smoke tests for the overview and every planned workspace."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from brand import PRODUCT_DESCRIPTOR, PRODUCT_NAME, TAGLINE
from ui.catalog import WORKSPACES

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class WorkspaceTests(unittest.TestCase):
    def test_overview_links_to_every_workspace(self):
        app = AppTest.from_file(APP, default_timeout=10).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, PRODUCT_NAME)
        self.assertNotIn(PRODUCT_DESCRIPTOR, [item.value for item in app.subheader])
        self.assertNotIn(PRODUCT_DESCRIPTOR, [item.value for item in app.caption])
        self.assertNotIn("Executive Overview", [item.value for item in app.caption])
        self.assertIn(f"**{TAGLINE}**", [item.value for item in app.markdown])
        headings = [item.value for item in app.header]
        self.assertLess(headings.index("What is HospitIQ?"), headings.index("Explore HospitIQ"))
        self.assertLess(headings.index("Explore HospitIQ"), headings.index("Strategic intelligence highlights"))
        self.assertIn("Fictional company · Illustrative financial assumptions", [item.value for item in app.caption])
        self.assertTrue(any("Positioning and customer fit guide" in item.value for item in app.markdown))
        self.assertTrue(any("Research snapshot as of" in item.value for item in app.markdown))
        self.assertTrue(any("synthetic customer data" in item.value for item in app.caption))
        self.assertEqual(
            [link.proto.label for link in app.get("page_link")],
            [workspace.title for workspace in WORKSPACES],
        )

    def test_advisor_route_is_available(self):
        workspace = next(item for item in WORKSPACES if item.slug == "ai-strategy-advisor")
        app = AppTest.from_file(APP, default_timeout=10).run().switch_page(workspace.script).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, workspace.title)
