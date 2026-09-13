from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from grant_funding_insights.matcher import FounderProfile, build_roadmap, rank_grants
from grant_funding_insights.sources import CuratedCsvSource


ROOT = Path(__file__).resolve().parent
READINESS_ITEMS = ["Entity registration", "Current financials", "Measurable outcomes",
                   "Project budget", "Application owner"]
FOCUS_AREAS = ["Economic development", "Workforce development", "Technology & innovation",
               "Research & development", "Community services", "Food access & agriculture",
               "Sustainability & energy", "Youth & education", "Arts & culture",
               "Health & wellness", "Veterans", "Exporting"]
STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
          "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
          "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
          "UT", "VT", "VA", "WA", "WV", "WI", "WY", "PR", "VI", "GU"]

SAMPLES = {
    "Community nonprofit": {
        "organization_name": "Neighborhood Opportunity Lab", "entity_type": "Nonprofit",
        "state": "TX", "rural": False, "years_operating": 6, "funding_need": 75000,
        "focus_areas": ["Economic development", "Workforce development"],
        "description": ("We provide entrepreneurship training, technical assistance, and workforce "
                        "pathways for disadvantaged microentrepreneurs and underserved founders."),
        "identity_flags": [],
        "readiness": {"Entity registration": True, "Current financials": True,
                      "Measurable outcomes": True, "Project budget": False,
                      "Application owner": True},
    },
    "Rural small business": {
        "organization_name": "Rural Roots Market", "entity_type": "Small business",
        "state": "TX", "rural": True, "years_operating": 3, "funding_need": 50000,
        "focus_areas": ["Sustainability & energy", "Food access & agriculture"],
        "description": ("A rural food business seeking efficient refrigeration and solar equipment "
                        "to lower energy costs and expand local food access."),
        "identity_flags": ["Women-owned"],
        "readiness": {"Entity registration": True, "Current financials": True,
                      "Measurable outcomes": False, "Project budget": True,
                      "Application owner": True},
    },
    "Technology startup": {
        "organization_name": "Civic Signal Labs", "entity_type": "Small business",
        "state": "CA", "rural": False, "years_operating": 1, "funding_need": 275000,
        "focus_areas": ["Technology & innovation", "Research & development"],
        "description": ("We are developing a high-risk artificial intelligence platform that helps "
                        "cities predict infrastructure failures and improve public safety."),
        "identity_flags": ["Women-owned"],
        "readiness": {"Entity registration": True, "Current financials": False,
                      "Measurable outcomes": True, "Project budget": False,
                      "Application owner": True},
    },
}

st.set_page_config(page_title="Grant Funding Intelligence", page_icon="🧭", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 4rem; max-width: 1240px;}
h1, h2, h3 {font-weight: 500 !important; letter-spacing: .01em;}
.eyebrow {font-family: sans-serif; text-transform: uppercase; letter-spacing: .14em;
          color: #7A5A08; font-size: .78rem; margin-bottom: .35rem;}
.hero {border-left: 5px solid #9A7412; padding: .25rem 0 .35rem 1.1rem; margin-bottom: 1.2rem;}
.quiet {color: #565656; font-family: sans-serif;}
.status {display: inline-block; border: 1px solid #6C6C6C; border-radius: 999px;
         padding: .18rem .62rem; margin-right: .35rem; font: 600 .78rem sans-serif;}
.status-open {background: #E8F4EA; color: #154B27; border-color: #4D835D;}
.status-watch {background: #FFF4D6; color: #644B08; border-color: #A98523;}
.status-stop {background: #FBE8E8; color: #7A2020; border-color: #A95A5A;}
[data-testid="stMetric"] {border: 1px solid #C9C9C1; border-radius: .6rem;
                          padding: .7rem 1rem; background: white;}
.source-note {border: 1px solid #C9C9C1; background: #F7F5EE; border-radius: .5rem;
              padding: .75rem 1rem; font-family: sans-serif; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)


def load_demo(name: str) -> None:
    sample = SAMPLES[name]
    for key, value in sample.items():
        if key != "readiness":
            st.session_state[f"input_{key}"] = value
    for item, complete in sample["readiness"].items():
        st.session_state[f"ready_{item}"] = complete
    st.session_state["profile"] = FounderProfile(**sample)


def initialize() -> None:
    if "profile" not in st.session_state:
        load_demo("Community nonprofit")


def money(value: float | None) -> str:
    return "Verify range" if value is None else f"${value:,.0f}"


def status_class(actionability: str) -> str:
    if actionability in {"Open pathway", "Referral pathway"}:
        return "status-open"
    if actionability == "Cycle watch":
        return "status-watch"
    return "status-stop"


def render_match(match, rank: int) -> None:
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"#### {rank}. {match.title}")
            st.caption(match.sponsor)
            st.markdown(f'<span class="status {status_class(match.actionability)}">'
                        f'{match.actionability}</span><span class="status">'
                        f'{match.eligibility}</span>', unsafe_allow_html=True)
        with right:
            st.metric("Fit score", f"{match.score}/100")
        st.progress(match.score / 100, text=f"Explainable fit: {match.score}%")
        st.write(match.summary)
        st.caption(f"Reference award range: {money(match.min_award)} – {money(match.max_award)}"
                   f"  •  {match.status_label}")
        why, caution = st.columns(2)
        with why:
            st.markdown("**Why it matched**")
            for item in match.strengths[:5]:
                st.write(f"✓ {item}")
        with caution:
            st.markdown("**Check before pursuing**")
            for item in match.gaps[:5] or ("No preliminary gaps found; human review still required.",):
                st.write(f"→ {item}")
        with st.expander("See score breakdown and source notes"):
            component_frame = pd.DataFrame({"Component": list(match.score_components.keys()),
                                            "Points": list(match.score_components.values())})
            st.dataframe(component_frame, hide_index=True, width="stretch")
            st.write(match.eligibility_notes)
            st.caption(f"Source snapshot last reviewed: {match.last_verified}")
        st.link_button("Open official source", match.source_url)


initialize()
grants = CuratedCsvSource(ROOT / "data" / "grants.csv").load()

with st.sidebar:
    st.markdown("### Quick-start profiles")
    demo_name = st.selectbox("Choose a guided example", list(SAMPLES))
    if st.button("Load example", width="stretch"):
        load_demo(demo_name)
        st.rerun()
    st.divider()
    st.markdown("### Reading the results")
    st.write("**Open pathway** — verify and consider now")
    st.write("**Referral pathway** — contact the named intermediary")
    st.write("**Cycle watch** — prepare for the next round")
    st.write("**Do not pursue** — a hard eligibility rule did not fit")
    st.caption("A match score is a decision aid. It is not a funding prediction.")

st.markdown('<div class="eyebrow">Founder decision-support prototype</div>', unsafe_allow_html=True)
st.markdown("""<div class="hero"><h1>Grant Funding Intelligence</h1>
<p class="quiet">See what fits, what does not, and what to do next.</p></div>""",
            unsafe_allow_html=True)
st.markdown('<div class="source-note"><b>Portfolio MVP:</b> This tool uses a curated '
            'public-program snapshot for demonstration. Always confirm the current notice, '
            'deadline, and eligibility at the official source before investing time or submitting.'
            '</div>', unsafe_allow_html=True)

profile_tab, matches_tab, dashboard_tab, roadmap_tab, method_tab = st.tabs(
    ["1. Founder profile", "2. Matches", "3. Dashboard", "4. Roadmap", "How it works"])

with profile_tab:
    st.subheader("Tell the system what you are building")
    st.write("Short answers are enough. The tool separates eligibility from strategic fit.")
    with st.form("founder_profile"):
        col1, col2 = st.columns(2)
        with col1:
            organization_name = st.text_input("Organization or project name",
                                              key="input_organization_name")
            entity_type = st.selectbox("Entity type", ["Small business", "Nonprofit"],
                                       key="input_entity_type")
            state = st.selectbox("Primary state or territory", STATES, key="input_state")
            rural = st.checkbox("The applicant or project is in a rural area", key="input_rural")
        with col2:
            years_operating = st.number_input("Years operating", min_value=0, max_value=100,
                                              step=1, key="input_years_operating")
            funding_need = st.number_input("Estimated funding need", min_value=0, step=1000,
                                           key="input_funding_need")
            identity_flags = st.multiselect("Relevant applicant qualifiers",
                                            ["Women-owned", "NASE member", "Agricultural producer"],
                                            key="input_identity_flags")
        focus_areas = st.multiselect("What outcomes will the funding support?", FOCUS_AREAS,
                                     key="input_focus_areas")
        description = st.text_area(
            "Describe the organization, community need, project, and intended results",
            height=130, key="input_description")
        st.markdown("#### Readiness check")
        ready_columns = st.columns(3)
        readiness = {}
        for index, item in enumerate(READINESS_ITEMS):
            with ready_columns[index % 3]:
                readiness[item] = st.checkbox(item, key=f"ready_{item}")
        submitted = st.form_submit_button("Update my matches", width="stretch")
        if submitted:
            st.session_state["profile"] = FounderProfile(
                organization_name=organization_name, entity_type=entity_type, state=state,
                rural=rural, years_operating=int(years_operating),
                funding_need=float(funding_need), focus_areas=tuple(focus_areas),
                description=description, identity_flags=tuple(identity_flags), readiness=readiness)
            st.success("Profile updated. Open the Matches tab to review the results.")

profile = st.session_state["profile"]
results = rank_grants(profile, grants)
eligible_results = [item for item in results if item.eligibility == "Eligibility screen passed"]
open_results = [item for item in eligible_results
                if item.actionability in {"Open pathway", "Referral pathway"}]
watch_results = [item for item in eligible_results if item.actionability == "Cycle watch"]
not_eligible = [item for item in results if item.eligibility == "Not currently eligible"]

with matches_tab:
    st.subheader(f"Preliminary matches for {profile.organization_name or 'this founder'}")
    st.write("Review the open and referral pathways first. Keep strong cycle-watch programs on the roadmap.")
    if open_results:
        st.markdown("### Open or referral pathways")
        for index, match in enumerate(open_results[:4], 1):
            render_match(match, index)
    if watch_results:
        st.markdown("### Prepare for the next cycle")
        for index, match in enumerate(watch_results[:4], 1):
            render_match(match, index)
    if not eligible_results:
        st.info("No programs passed the preliminary eligibility screen. Review the reasons below.")
    with st.expander(f"See {len(not_eligible)} programs screened out"):
        for match in not_eligible:
            st.markdown(f"**{match.title}** — {match.score}/100 strategic fit")
            for gap in match.gaps:
                if any(word in gap.casefold() for word in ("mismatch", "requires", "must", "missing required")):
                    st.write(f"• {gap}")

with dashboard_tab:
    st.subheader("Funding decision dashboard")
    top_score = max((item.score for item in eligible_results), default=0)
    known_max = sum(item.max_award or 0 for item in open_results
                    if item.score >= 50 and item.max_award is not None)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Programs reviewed", len(results))
    metric_cols[1].metric("Open/referral pathways", len(open_results))
    metric_cols[2].metric("Cycle-watch fits", len(watch_results))
    metric_cols[3].metric("Highest fit score", f"{top_score}/100")
    chart_data = pd.DataFrame({"Program": [item.title for item in eligible_results],
                              "Fit score": [item.score for item in eligible_results],
                              "Pathway": [item.actionability for item in eligible_results]})
    if not chart_data.empty:
        chart_data = chart_data.sort_values("Fit score", ascending=True)
        color_map = {"Open pathway": "#2E6B45", "Referral pathway": "#527A63",
                     "Cycle watch": "#9A7412"}
        figure = px.bar(chart_data, x="Fit score", y="Program", color="Pathway",
                        orientation="h", text="Fit score", color_discrete_map=color_map,
                        range_x=[0, 100])
        figure.update_layout(height=max(360, 58 * len(chart_data)),
                             margin=dict(l=10, r=15, t=25, b=10),
                             legend_title_text="Decision status",
                             font=dict(family="Arial", color="#151515"))
        figure.update_traces(texttemplate="%{text}/100", textposition="outside")
        st.plotly_chart(figure, width="stretch")
    if known_max:
        st.caption(f"Illustrative published maximum across open matches scoring 50+: "
                   f"${known_max:,.0f}. This is not expected revenue, an award forecast, "
                   "or a recommendation to request the maximum.")
    component_rows = []
    for item in eligible_results[:5]:
        for component, points in item.score_components.items():
            component_rows.append({"Program": item.title, "Component": component, "Points": points})
    if component_rows:
        st.markdown("### Why the scores differ")
        component_frame = pd.DataFrame(component_rows)
        component_chart = px.bar(component_frame, x="Program", y="Points", color="Component",
                                 color_discrete_sequence=["#171717", "#9A7412", "#C4A349",
                                                          "#777777", "#BFC1BD"])
        component_chart.update_layout(barmode="stack", yaxis_title="Points toward 100",
                                      xaxis_title=None, legend_title_text="Scoring component",
                                      font=dict(family="Arial"))
        st.plotly_chart(component_chart, width="stretch")

with roadmap_tab:
    st.subheader("Funding roadmap")
    roadmap_candidates = open_results + watch_results
    if roadmap_candidates:
        labels = [f"{item.title} — {item.score}/100" for item in roadmap_candidates]
        selected_label = st.selectbox("Build the roadmap around", labels)
        selected = roadmap_candidates[labels.index(selected_label)]
        st.caption(f"Decision status: {selected.actionability}. "
                   f"Source snapshot reviewed {selected.last_verified}.")
        for step in build_roadmap(profile, selected):
            with st.expander(f"{step['phase']}  •  {step['timing']}",
                             expanded=step["phase"].startswith("1.")):
                st.write(step["goal"])
                for task in step["tasks"]:
                    st.checkbox(str(task), key=f"roadmap_{selected.grant_id}_{step['phase']}_{task}")
    else:
        st.info("Complete the founder profile to create a roadmap from an eligible match.")

with method_tab:
    st.subheader("Transparent by design")
    st.write("The tool uses hard eligibility gates first, then ranks strategic fit. It never predicts an award.")
    method = pd.DataFrame([
        ["Mission/NLP", "35 points", "TF-IDF similarity between the founder narrative and program language"],
        ["Focus areas", "25 points", "Overlap between selected outcomes and program priorities"],
        ["Funding range", "15 points", "How well the request fits the reference award range"],
        ["Geography", "10 points", "National or state-level geographic fit"],
        ["Readiness", "15 points", "Completion of five visible readiness conditions"],
    ], columns=["Component", "Weight", "Plain-language meaning"])
    st.dataframe(method, hide_index=True, width="stretch")
    st.markdown("### Human review remains required")
    st.write("Source terms change. Legal eligibility can depend on details that a short profile cannot capture. "
             "A qualified person must verify the current notice, applicant status, registrations, budget, "
             "match, allowable costs, and submission rules.")
    st.markdown("### Data responsibility")
    st.write("This MVP stores no submitted profile data, uses no protected demographic data in its score, "
             "and exposes every scoring component to the user.")

st.divider()
st.caption("Portfolio MVP by Rolanda Anwar — Founder | Principal Enterprise Architect  •  "
           "Às̩e̩ Advisory and Tech")
