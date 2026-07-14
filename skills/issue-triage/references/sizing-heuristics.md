# T-shirt sizing heuristics

Map scope qualities to one label — not gut feel.

| Size | Heuristic |
| --- | --- |
| **XS** | One demoable unit; junior can implement without guessing; almost no ambiguity |
| **S** | One clear vertical slice; few files; acceptance criteria obvious |
| **M** | A few demoable slices or moderate surface area; still junior-implementable with the sealed body |
| **L** | Multiple slices or significant ambiguity until sealed; consider splitting before ready |
| **XL** | Too large / too vague for one ready Issue — split; do not seal as-is |

Also ask: too large? too small? how many demoable units? would a junior guess?

## Auto-impl gate (triage handoff)

Only `size/XS` and `size/S` plus `ready` are treated as auto-impl eligible.
`M` / `L` / `XL` stay human-steered even if sealed with `ready`.

Put the chosen size and a one-line rationale in the Issue body’s `## Size`
section and apply the matching `size/*` label.
