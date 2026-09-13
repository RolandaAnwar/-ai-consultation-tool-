from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class DashboardSmokeTests(unittest.TestCase):
    def test_guided_default_profile_renders_full_decision_flow(self):
        app = AppTest.from_file(str(ROOT / "dashboard_app.py"), default_timeout=30)
        app.run()

        self.assertEqual(list(app.exception), [])
        self.assertEqual(
            [tab.label for tab in app.tabs],
            [
                "1. Founder profile",
                "2. Matches",
                "3. Dashboard",
                "4. Roadmap",
                "How it works",
            ],
        )
        self.assertTrue(any(metric.label == "Programs reviewed" for metric in app.metric))
        self.assertTrue(any(button.label == "Update my matches" for button in app.button))


if __name__ == "__main__":
    unittest.main()

