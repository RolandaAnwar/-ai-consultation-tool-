"""Explainable grant matching for founders and community organizations."""

from .matcher import FounderProfile, MatchResult, build_roadmap, rank_grants
from .sources import CuratedCsvSource, GrantsGovConnector

__all__ = [
    "FounderProfile",
    "MatchResult",
    "build_roadmap",
    "rank_grants",
    "CuratedCsvSource",
    "GrantsGovConnector",
]

