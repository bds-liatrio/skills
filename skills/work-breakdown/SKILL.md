---
name: work-breakdown
description: Analyzes a large piece of scope / work and provides recommendations on how to split the work into smaller units of work, identifying dependencies and opportunities for parallelization. Use when given an ambiguous, high-level requirement that may span multiple discrete systems, projects, or repositories and needs to be decomposed before any design or implementation begins.
---

# Work Breakdown

Analyze the provided features/issues and produce a breakdown of work suitable for parallel or sequential execution.

## Process

1. **Gather context** — Fetch issue details, read relevant source code using the `codebase-exploration` skill and the `research_codebase` skill (for more detailed analysis - when required)
2. **Identify work units** — Break input into discrete, independently deliverable units - these units of work should be independently verifiable, either manually or using automated testing.
3. **Map dependencies** — Which units depend on others? What must be sequenced vs parallelized?
4. **Assess risks** — Flag units of work that touch the same file, projects/repositories, entities, or layers (merge conflict risk, network layer, data layer, etc.) across multiple systems
5. **Recommend execution order** — Suggest which units can run in parallel and which should be sequenced

## Output

Present a concise breakdown to the user:
- List of work units with one-line descriptions
- Dependency graph (which blocks which) - this should be a minimal visual representation
- Risk flags
- Recommended implementation strategy

Do NOT make requirements or design decisions — just identify the shape of the work.
