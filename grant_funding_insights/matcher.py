"""Explainable eligibility, fit, and readiness scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class FounderProfile:
    organization_name: str
    entity_type: str
    state: str
    rural: bool
    years_operating: int
    funding_need: float
    focus_areas: tuple[str, ...]
    description: str
    identity_flags: tuple[str, ...] = ()
    readiness: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class MatchResult:
    grant_id: str
    title: str
    sponsor: str
    score: int
    eligibility: str
    actionability: str
    strengths: tuple[str, ...]
    gaps: tuple[str, ...]
    score_components: dict[str, int]
    min_award: float | None
    max_award: float | None
    status_label: str
    deadline: object
    focus_areas: tuple[str, ...]
    summary: str
    eligibility_notes: str
    readiness_items: tuple[str, ...]
    source_url: str
    last_verified: str


WEIGHTS = {"mission": 35, "focus": 25, "amount": 15, "geography": 10, "readiness": 15}


def _clean_set(values: Iterable[str]) -> set[str]:
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def _mission_similarities(profile: FounderProfile, grants: pd.DataFrame) -> list[float]:
    profile_text = " ".join([profile.description, *profile.focus_areas]).strip()
    grant_texts = [
        " ".join([str(row.title), str(row.summary), " ".join(row.focus_areas)])
        for row in grants.itertuples()
    ]
    if not profile_text or not any(text.strip() for text in grant_texts):
        return [0.0] * len(grant_texts)

    try:
        matrix = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=1
        ).fit_transform([profile_text, *grant_texts])
    except ValueError:
        return [0.0] * len(grant_texts)

    raw = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    return [min(1.0, float(value) * 2.5) for value in raw]


def _focus_fit(profile: FounderProfile, grant_focus: Iterable[str]) -> float:
    wanted = _clean_set(profile.focus_areas)
    offered = _clean_set(grant_focus)
    if not wanted:
        return 0.0
    return len(wanted.intersection(offered)) / len(wanted)


def _amount_fit(need: float, minimum: float, maximum: float) -> tuple[float, str]:
    if pd.isna(minimum) or pd.isna(maximum) or maximum <= 0:
        return 0.6, "Award range needs verification"
    if minimum <= need <= maximum:
        return 1.0, "Funding request fits the published range"
    if need < minimum:
        ratio = need / minimum if minimum else 1.0
        return max(0.35, ratio), "Requested amount is below the typical minimum"
    ratio = maximum / need if need else 0.0
    return max(0.15, ratio), "Requested amount exceeds the typical maximum"


def _eligibility(profile: FounderProfile, row: object) -> tuple[bool, list[str], list[str]]:
    failures: list[str] = []
    passes: list[str] = []

    entity_types = _clean_set(row.entity_types)
    if profile.entity_type.casefold() in entity_types:
        passes.append(f"Entity type accepted: {profile.entity_type}")
    else:
        failures.append(f"Entity type mismatch: accepts {', '.join(row.entity_types)}")

    states = _clean_set(row.states)
    if "all" in states or profile.state.casefold() in states:
        passes.append("Geographic requirement appears to fit")
    else:
        failures.append(f"Geography mismatch: limited to {', '.join(row.states)}")

    if bool(row.rural_only) and not profile.rural:
        failures.append("Applicant or project must be in an eligible rural area")
    elif bool(row.rural_only):
        passes.append("Rural-location requirement appears to fit")

    if not pd.isna(row.min_years) and profile.years_operating < int(row.min_years):
        failures.append(f"Requires at least {int(row.min_years)} years of operation")
    elif not pd.isna(row.min_years) and row.min_years > 0:
        passes.append("Operating-history requirement appears to fit")

    profile_flags = _clean_set(profile.identity_flags)
    required_flags = _clean_set(row.required_flags)
    missing_flags = required_flags.difference(profile_flags)
    if missing_flags:
        failures.append(f"Missing required qualifier: {', '.join(sorted(missing_flags))}")
    elif required_flags:
        passes.append("Special applicant qualifier appears to fit")

    return not failures, passes, failures


def rank_grants(profile: FounderProfile, grants: pd.DataFrame) -> list[MatchResult]:
    """Rank grants while keeping eligibility, fit, and readiness separate."""

    if grants.empty:
        return []

    similarities = _mission_similarities(profile, grants)
    readiness_ratio = sum(bool(value) for value in profile.readiness.values()) / max(
        1, len(profile.readiness)
    )
    results: list[MatchResult] = []

    for similarity, row in zip(similarities, grants.itertuples()):
        eligible, passes, failures = _eligibility(profile, row)
        focus_fit = _focus_fit(profile, row.focus_areas)
        amount_fit, amount_note = _amount_fit(
            profile.funding_need, row.min_award, row.max_award
        )
        geography_fit = 1.0 if not any("Geography mismatch" in item for item in failures) else 0.0

        components = {
            "Mission/NLP": round(similarity * WEIGHTS["mission"]),
            "Focus areas": round(focus_fit * WEIGHTS["focus"]),
            "Funding range": round(amount_fit * WEIGHTS["amount"]),
            "Geography": round(geography_fit * WEIGHTS["geography"]),
            "Readiness": round(readiness_ratio * WEIGHTS["readiness"]),
        }
        score = max(0, min(100, sum(components.values())))

        strengths = list(passes)
        if similarity >= 0.55:
            strengths.append("Strong narrative and mission similarity")
        elif similarity >= 0.25:
            strengths.append("Some narrative and mission similarity")
        if focus_fit >= 0.5:
            strengths.append("Priority areas overlap")
        if amount_fit >= 0.95:
            strengths.append(amount_note)

        gaps = list(failures)
        if amount_fit < 0.95:
            gaps.append(amount_note)
        missing_readiness = [item for item, complete in profile.readiness.items() if not complete]
        if missing_readiness:
            gaps.append("Readiness work: " + ", ".join(missing_readiness))

        eligibility = "Eligibility screen passed" if eligible else "Not currently eligible"
        if not eligible:
            actionability = "Do not pursue"
        elif str(row.open_state).casefold() == "open":
            actionability = "Open pathway"
        elif str(row.open_state).casefold() == "referral":
            actionability = "Referral pathway"
        else:
            actionability = "Cycle watch"

        results.append(MatchResult(
            grant_id=str(row.grant_id), title=str(row.title), sponsor=str(row.sponsor),
            score=score, eligibility=eligibility, actionability=actionability,
            strengths=tuple(dict.fromkeys(strengths)), gaps=tuple(dict.fromkeys(gaps)),
            score_components=components,
            min_award=None if pd.isna(row.min_award) else float(row.min_award),
            max_award=None if pd.isna(row.max_award) else float(row.max_award),
            status_label=str(row.status_label), deadline=row.deadline,
            focus_areas=tuple(row.focus_areas), summary=str(row.summary),
            eligibility_notes=str(row.eligibility_notes),
            readiness_items=tuple(row.readiness_items), source_url=str(row.source_url),
            last_verified=str(row.last_verified),
        ))

    action_rank = {"Open pathway": 0, "Referral pathway": 1, "Cycle watch": 2, "Do not pursue": 3}
    return sorted(results, key=lambda item: (action_rank[item.actionability], -item.score, item.title))


def build_roadmap(profile: FounderProfile, match: MatchResult) -> list[dict[str, object]]:
    """Create a plain-language, evidence-led funding roadmap for one match."""

    missing = [item for item, complete in profile.readiness.items() if not complete]
    source_step = (
        "Confirm the current notice, deadline, award range, and exact eligibility "
        f"at the official source. Snapshot verified {match.last_verified}."
    )
    readiness_tasks = missing or ["Confirm registrations are current", "Assign an application owner"]
    return [
        {"phase": "1. Verify before investing time", "timing": "Day 1",
         "goal": "Turn the preliminary match into a verified go, watch, or stop decision.",
         "tasks": [source_step, match.eligibility_notes, "Record a human eligibility decision."]},
        {"phase": "2. Close readiness gaps", "timing": "Days 2–7",
         "goal": "Make the organization administratively ready.", "tasks": readiness_tasks},
        {"phase": "3. Build the evidence package", "timing": "Week 2",
         "goal": "Connect the need, activities, budget, and measurable public benefit.",
         "tasks": ["Document baseline conditions and target outcomes.",
                   "Create the logic model, milestones, and responsible owners.",
                   "Align the project budget with allowable costs and required match."]},
        {"phase": "4. Draft and review", "timing": "Weeks 3–4",
         "goal": "Produce a compliant, clear, and evidence-supported application.",
         "tasks": ["Draft directly against the funder's scoring criteria.",
                   "Complete compliance, budget, and source checks.",
                   "Use an independent human reviewer before submission."]},
        {"phase": "5. Submit, track, and learn", "timing": "Before deadline and after",
         "goal": "Protect the submission record and improve the next decision.",
         "tasks": ["Submit before the internal deadline and save confirmation.",
                   "Track questions, decision dates, and reporting commitments.",
                   "Record the result and lessons without treating a match score as an award prediction."]},
    ]

