"""Grant data-source contracts.

The MVP runs from a reviewed CSV snapshot. A deliberately small live-source
interface makes the next integration visible without making network access a
hidden runtime dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd


REQUIRED_COLUMNS = {
    "grant_id", "title", "sponsor", "entity_types", "states", "rural_only",
    "required_flags", "min_years", "min_award", "max_award", "open_state",
    "status_label", "deadline", "focus_areas", "summary", "eligibility_notes",
    "readiness_items", "source_url", "last_verified",
}


class GrantSource(Protocol):
    """Minimal contract shared by curated and future live sources."""

    def load(self) -> pd.DataFrame:
        """Return normalized grant records."""


def _split_pipe(value: object) -> tuple[str, ...]:
    if value is None or pd.isna(value):
        return ()
    return tuple(part.strip() for part in str(value).split("|") if part.strip())


def normalize_grants(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a grant frame into the matcher data contract."""

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Grant source is missing columns: {', '.join(sorted(missing))}")

    normalized = frame.copy()
    for column in (
        "entity_types", "states", "required_flags", "focus_areas", "readiness_items"
    ):
        normalized[column] = normalized[column].apply(_split_pipe)

    normalized["rural_only"] = (
        normalized["rural_only"].astype(str).str.lower().isin({"true", "1", "yes"})
    )
    for column in ("min_years", "min_award", "max_award"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized["deadline"] = pd.to_datetime(
        normalized["deadline"], errors="coerce"
    ).dt.date
    return normalized


@dataclass(frozen=True)
class CuratedCsvSource:
    """Reviewed, reproducible public-program snapshot used by the MVP."""

    path: Path

    def load(self) -> pd.DataFrame:
        return normalize_grants(pd.read_csv(self.path))


@dataclass(frozen=True)
class GrantsGovConnector:
    """Boundary for a future Grants.gov/Simpler.Grants.gov integration."""

    api_base_url: str = "https://api.simpler.grants.gov"
    enabled: bool = False

    def load(self) -> pd.DataFrame:
        if not self.enabled:
            raise RuntimeError(
                "Live ingestion is disabled in this MVP. Use CuratedCsvSource, "
                "or explicitly configure and test the Grants.gov connector."
            )
        raise NotImplementedError(
            "Implement authenticated search, pagination, freshness checks, "
            "deduplication, and normalization before enabling live ingestion."
        )

