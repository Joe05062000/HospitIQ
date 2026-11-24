# HospitIQ Phase 8 decision policy

Strategy Advisor now presents an executive recommendation separately from the catalog evidence and local financial results. This policy supports management review. It does not authorize spending or upgrade modeled results into forecasts.

## Decision inputs and scope

- The selected question, vendors, customer segment and theme define the evidence scope. Growth discovery uses the existing weighted ranking and, where available, the matching Product Growth handoff. Evidence confidence remains distinct from attractiveness.
- The investment screen uses the matching simulator handoff for a single product and segment. It needs Conservative, Base and Ambitious outputs. The existing model remains the source of cash, investment, payback, and sensitivity figures.
- Management supplies an objective, maximum modeled upfront investment, downside tolerance and target Base payback. All limits are blank by default. Qualification is a management declaration for the modeled scope covering eligible non-adopters, priced demand and supported implementation. There is no customer-level input in the Advisor.
- Supporting evidence keeps citations with reviewed claims. Related market or benchmarking evidence is attached when it shares a source with the chosen opportunity. Gaps and conflicting qualification evidence are shown as limits.

## Financial screening

| Check | Policy |
|---|---|
| Base economics | Three-year Base net cash must be positive to screen for a pilot. A downside scenario alone does not determine the outcome. |
| Investment cap | Compare the largest modeled upfront investment across all three scenarios with management’s cap. A pilot budget is a separate approval. |
| Downside tolerance | Compare the maximum loss in the scenarios with the permitted three-year cash loss. If a saved single-driver business stress produces a lower cash outcome, use that lower outcome. |
| Target payback | Compare unrounded approximate Base payback from rollout with the target. Non-recovery fails a supplied target. With no Base upfront investment the check is inapplicable. |
| Qualification | A modeled pass requires management to confirm eligibility, priced demand and implementation feasibility before the policy suggests a controlled pilot. |

Equal relative shocks identify influential inputs. They do not define a plausible downside or a probability. The separate business bounds are user assumptions and are applied one driver at a time. The report identifies which scenario those sensitivities belong to. If no matching bounds were saved, the downside check uses scenario cash alone.

## Recommendation precedence

1. Missing reviewed evidence or conflicting qualification evidence produces **Insufficient evidence to recommend a commitment**. An investment with a verified qualification blocker produces **Defer investment**.
2. With all three scenarios present, all-negative three-year cash produces **Defer investment** for the current proposal. A nonpositive Base with upside remaining, or a failed cap, downside or payback gate, produces **Redesign the opportunity**. The output names the failed checks.
3. Missing management limits or incomplete financial cases prevent a pilot recommendation. Passing modeled checks with unresolved qualification produces **Investigate further**.
4. Complete, passing checks and confirmed qualification produce **Conduct a controlled pilot**. Management still needs to cap pilot spend, define success and stop conditions, and update the scenarios before scaling.
5. The growth question can **Prioritize** a discovery candidate by the existing attractiveness score. Market signals are listed by title and matched to filters, rather than ranked by date. Competitive differentiation, cross-sell risk and the payments versus automation question propose a specific evidence-gathering step, with no forced investment decision.

The current policy evaluates one financial opportunity at a time. It can show discovery alternatives and compare qualitative trade-offs. It does not calculate a cross-product financial ranking; such a comparison would require comparable snapshots and an agreed objective.

## Regression example

Harborlight's fictional rollout retains its validated cash outcomes of −USD 1,206,250.00, +USD 647,808.00, and +USD 1,800,741.40. With **illustrative** limits of USD 1.0 million upfront investment, USD 1.5 million downside, and 36-month Base payback, a management-confirmed cohort screens for a controlled pilot. At a 24-month target, the same inputs trigger redesign because Base payback is approximately 30 months from rollout. With the same illustrative caps and unknown qualification, the policy calls for further investigation. No illustrative limits are prefilled in the UI.
