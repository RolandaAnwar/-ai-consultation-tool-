# Scoring and decision rules

The MVP treats three questions separately:

1. **Eligibility:** May this applicant pursue this program based on the fields we can screen?
2. **Strategic fit:** How closely do the project, priorities, geography, and funding need align?
3. **Readiness:** How much basic application infrastructure is already in place?

## Hard eligibility screen

The initial screen checks entity type, geography, rural location when required, minimum operating history, and required applicant qualifiers captured by the profile.

A failed hard rule produces **Do not pursue**. The strategic-fit score remains visible because it can still explain why a program looked attractive and help identify a future partnership or entity-structure question. It does not override the failed rule.

## Weighted fit score

| Component | Points | Method |
|---|---:|---|
| Mission/NLP | 35 | TF-IDF similarity between founder narrative and the program title, summary, and priorities |
| Focus areas | 25 | Exact overlap across the selected outcome taxonomy |
| Funding range | 15 | Full credit inside the published reference range; bounded partial credit outside it |
| Geography | 10 | Full credit for a national or matching-state program |
| Readiness | 15 | Share of five visible readiness items marked complete |

The final score is bounded from 0 to 100. Every component is shown in the interface.

## Status is not a score

- **Open pathway:** The program has an open or ongoing entry path in the reviewed source snapshot.
- **Referral pathway:** A founder must work through a state, territory, or other intermediary.
- **Cycle watch:** The referenced cycle is closed or a future notice must be verified.
- **Do not pursue:** At least one captured hard eligibility requirement did not fit.

## Responsible-use boundaries

- The score is not an award prediction or legal determination.
- No protected demographic characteristic adds score points.
- A required program qualifier can screen eligibility only when a user voluntarily supplies it.
- Source links and snapshot dates are visible.
- Human review is required before an application decision.
- Closed programs remain useful as roadmap signals, but are not presented as open money.

