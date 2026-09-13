from pathlib import Path
import unittest

from grant_funding_insights.matcher import FounderProfile, build_roadmap, rank_grants
from grant_funding_insights.sources import CuratedCsvSource


ROOT = Path(__file__).resolve().parents[1]


def profile(**changes):
    values = {
        "organization_name": "Neighborhood Opportunity Lab", "entity_type": "Nonprofit",
        "state": "TX", "rural": False, "years_operating": 6, "funding_need": 75000,
        "focus_areas": ("Economic development", "Workforce development"),
        "description": ("We provide entrepreneurship training, technical assistance, and workforce "
                        "pathways for disadvantaged microentrepreneurs and underserved founders."),
        "identity_flags": (),
        "readiness": {"Entity registration": True, "Current financials": True,
                      "Measurable outcomes": True, "Project budget": False,
                      "Application owner": True},
    }
    values.update(changes)
    return FounderProfile(**values)


class MatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grants = CuratedCsvSource(ROOT / "data" / "grants.csv").load()

    def test_scores_stay_in_range(self):
        results = rank_grants(profile(), self.grants)
        self.assertTrue(results)
        self.assertTrue(all(0 <= result.score <= 100 for result in results))

    def test_entity_type_is_a_hard_eligibility_gate(self):
        result = next(item for item in rank_grants(profile(), self.grants)
                      if item.grant_id == "NSF-SEED")
        self.assertEqual(result.eligibility, "Not currently eligible")
        self.assertEqual(result.actionability, "Do not pursue")

    def test_rural_requirement_is_explained(self):
        rural_result = next(
            item for item in rank_grants(
                profile(entity_type="Small business", rural=False), self.grants
            ) if item.grant_id == "USDA-REAP"
        )
        self.assertTrue(any("rural area" in gap for gap in rural_result.gaps))

    def test_relevant_microenterprise_program_ranks_as_future_fit(self):
        results = rank_grants(profile(), self.grants)
        eligible_watch = [item for item in results if item.actionability == "Cycle watch"]
        self.assertEqual(eligible_watch[0].grant_id, "SBA-PRIME")

    def test_roadmap_includes_readiness_gap(self):
        match = next(item for item in rank_grants(profile(), self.grants)
                     if item.grant_id == "SBA-PRIME")
        roadmap = build_roadmap(profile(), match)
        self.assertEqual(len(roadmap), 5)
        self.assertIn("Project budget", roadmap[1]["tasks"])


if __name__ == "__main__":
    unittest.main()

