# Sealed Issue body skeleton

Use this structure for the GitHub Issue body after triage. Sections above the
rule are the executable spec; `## Original Ask` is always last.

```markdown
## Goals
…

## Non-goals
…

## Functional Requirements
1. …

## Constraints
…

## Assumptions
…

## Size
<XS|S|M|L|XL> — <one-line heuristic rationale>

## User Acceptance Criteria
- [ ] …

## Testable / Verifiable
1. …

---

## Original Ask

<verbatim pre-triage body; demote nested ATX headings by one level, e.g.
### Summary instead of ## Summary, so they do not collide with sealed ## sections>
```

## Original Ask rules (I5)

1. Bottom of the body only.
2. Preceded by `---`.
3. Demote or fence headings inside the snapshot.
4. Snapshot the body as it existed **before** first seal overwrite.
