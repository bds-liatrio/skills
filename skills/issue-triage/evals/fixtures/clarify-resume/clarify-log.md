# Issue triage clarify — example/petclinic#11
round: 1 / 4

## Round 1
### Q1 — What should improve?
Why: Body is only "Make it better" — no goal without a target surface
- **A)** Locale switcher (EN/ES) in the header — common i18n ask; narrow and demoable
- **B)** Performance pass on home page — measurable but vague without a budget
- **C)** Dark mode toggle — UI-wide; likely larger than one issue
- **D)** Other — user specifies
Recommended: A — smallest concrete product ask that matches "improve something"
Answer: A

### Q2 — Where should the control live?
Why: Layout/placement changes which files an agent must touch
- **A)** Global header nav — one shared layout; consistent discovery
- **B)** User settings page only — fewer touchpoints; easy to miss
- **C)** Footer only — low visibility; odd for locale
- **D)** Other — user specifies
Recommended: A — locale affects whole session; header is the usual pattern
Answer: _pending_

### Q3 — Persistence / defaults?
Why: Cookie vs profile vs URL param changes constraints and tests
- **A)** Cookie (max-age 1y), default browser locale — no auth required; simple tests
- **B)** Server-side user profile — needs auth/account model
- **C)** URL query param only — shareable but noisy URLs
- **D)** Other — user specifies
Recommended: A — works for anonymous users; easy to verify
Answer: _pending_
