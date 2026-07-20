# Explanation Artifact Contract

The artifact is a single self-contained HTML file written under `.lavish/`.
Everything below is a requirement unless marked as guidance.

## Document Structure

- **One continuous page** — section headers and vertical scroll, never tabs.
- **Header**: a `.shell` grid with a sticky `.toc-col` (left) and the `article`
  (right) — see [explanation-stylesheet.css](explanation-stylesheet.css)
  `.shell`/`nav.toc`. The masthead inside `article` carries a `.kicker` label,
  `h1` change title, italic `.standfirst` one-sentence summary, and a `.meta`
  row (input mode, diff size, date).
- **Table of contents**: `nav.toc` with scroll-spy — the active section's link
  gets `.active` as the reader scrolls (see explanation-script.js's
  `IntersectionObserver` block). Omit the Quiz entry when the quiz is skipped.
  Collapses to a tap-to-expand header below 880px (already handled by the
  stylesheet/script).
- **Four sections**, each with a stable `id` for TOC anchors: `id="background"`,
  `id="intuition"`, `id="code"`, `id="quiz"`.
- **Responsive**: readable on a phone. The stylesheet's `@media` blocks already
  collapse the TOC column and reflow diagrams below 880px/560px — reuse them
  rather than writing new breakpoints.
- **Self-contained**: all CSS in one `<style>` block (copy
  [explanation-stylesheet.css](explanation-stylesheet.css) verbatim), all JS
  in one `<script>` block (start from
  [explanation-script.js](explanation-script.js)), diagrams as inline HTML
  using the two diagram families below. Zero external requests — no CDN fonts,
  no image files, no `src`/`href` pointing at `http(s)://`. The stylesheet's
  `--serif`/`--sans`/`--mono` variables name display fonts as a first preference
  (safe: naming an unavailable local font is not a network fetch) and fall back
  to system fonts already listed in each stack.

## Section Contracts

### 1. Background

Teach the surrounding system before mentioning the diff. Two layers, in order:

- **Beginner layer**: what this part of the system is for, in plain language a
  newcomer to the codebase can follow. Wrap this layer in
  `<details class="skippable">` (see the stylesheet) with a `summary` inviting a
  reader who already knows the system to skip ahead — canonical mechanism for
  serving both audiences without forcing either to scroll past content meant for
  the other.
- **Change-specific layer**: the specific components the diff touches, what they
  did *before* the change, and why that behavior needed to change. Always
  visible — never inside the skippable block.

When a spec/validation/review report was ingested, anchor this section to the
stated requirements ("the spec calls for X; before this change the system did Y").

### 2. Intuition

The core essence of the change, taught through concreteness:

- Use **toy data and worked examples** — trace one small realistic input through
  the old behavior, then the new.
- Use **figures and diagrams liberally**, built from the two reusable diagram
  families in [explanation-stylesheet.css](explanation-stylesheet.css) — never
  ASCII art, and reach for hand-rolled inline SVG only when neither family fits:
  - **Flow** (`.diagram .flow .node .arrow`): boxes for system components
    connected by labelled arrows, the example data written on the arrow's
    `.lab`. Use `.arrow.hit`/`.arrow.miss` (green/red) to mark the two paths a
    request can take.
  - **Timeline** (`.diagram .timeline .lane .track .span`): horizontal lanes =
    concurrent actors over time, each `.span` a labelled interval. Wrap two
    timelines in `.diagram .split .before`/`.after` to compare before/after
    behavior on matching axes.
  - A `.stats` row of `.stat` tiles is optional but encouraged whenever the
    change has a quantifiable before/after (queries per event, latency, request
    count).
- Make at least one figure manipulable — a micro-interactable the reader
  operates to see the behavior change (see Micro-Interactions below).
- End with the one-paragraph "aha": what single idea, once grasped, makes the
  whole diff obvious.

### 3. Code

A high-level walkthrough, grouped in an order that makes sense to a human — by
logical cluster (core change → supporting changes → tests/config), not by file
path order.

- For each cluster: what it does, why it's there, then the key excerpt.
- Code excerpts go in `.code-wrap` blocks (`.code-title` with a `.path`/`.lang`,
  then `<pre>`) per the stylesheet — `white-space: pre` preserves indentation.
  Keep excerpts short — the interesting hunk, not whole files. For a diff-style
  excerpt, wrap added/removed lines in `<span class="ln-add">`/`<span class="ln-del">`
  so they render with the same green/red treatment as the Intuition section's
  diagrams; use `.code-wrap.plain` (no `.code-title`) for a non-diff excerpt.
- For very large diffs, walk representative files in depth and summarize the
  rest explicitly ("the remaining 12 files apply the same rename").

### 4. Quiz

Five multiple-choice questions, medium difficulty, testing **substantive
understanding** of the change — the kind of thing a reviewer should know after
reading the page. Never trivia ("what line number…") or gotchas.

Interactive behavior (embedded JS):

- Selecting an answer immediately reveals right/wrong plus a one-sentence explanation.
- Wrong answers show the explanation for why that choice is tempting but incorrect.
- No score submission, no persistence — it's a self-check.

Write each question's `opts` array with the correct choice wherever it reads most
naturally — do not manually distribute correct answers across A/B/C/D/E. The
canonical script shuffles each question's options at render time specifically so
a natural (often clustered) authoring order never becomes a visible pattern.

## Micro-Interactions

Interactivity exists to explain, and belongs inline with the content it explains:

- **At least one micro-interactable in the Intuition section** — preferred forms:
  - **Before/after toggle**: one click swaps a diagram between old and new behavior.
  - **Step-through data flow**: Next/Back advances example data along arrows.
  - **Hover/tap reveal**: pointing at a node surfaces the example value or rule.
- Each interaction must teach something a static figure can't — if removing it
  loses no understanding, cut it.
- The initial state must stand alone: the page still makes sense printed or with
  JS blocked.
- Plain `<button>` / `<details>` elements, keyboard-operable, no libraries.

The Quiz's answer-reveal is part of this same philosophy.

## Callouts

Use `.callout` boxes throughout, each with an `.ic` label. Map conceptual kinds
onto the stylesheet variants by label text:

- **Key concept** (`.callout.def`, blue) — label `.ic` "Def".
- **Edge case** (`.callout.warn`, amber) — label `.ic` "Edge".
- **Watch out** (`.callout.warn`, amber) — label `.ic` "Watch out" or "Why".

## Writing Style

Aim for the clarity and flow of Martin Kleppmann's technical writing: engaging,
classic style, plain sentences, smooth transitions. Serve beginners with the
Background layer while keeping enough depth that a senior engineer unfamiliar
with this subsystem still learns something.

## Design System (required)

The visual design is fixed — copy
[explanation-stylesheet.css](explanation-stylesheet.css) into the `<style>`
block and [explanation-script.js](explanation-script.js) into the `<script>`
block verbatim; only the QUESTIONS array, the diagram markup, and any
page-specific micro-interaction handlers are new per run. Do not re-derive the
palette, type scale, or component classes — warm-paper "essay" reading surface
(serif body, sans headings, mono code), a single quiet accent color, and the
component classes documented throughout this contract (`.callout`, `.code-wrap`,
`.diagram`, `.stats`, `.q`/`.opts`, `details.skippable`).

## Secret Hygiene

Before writing the file, scan embedded diff content for credential-shaped values
(keys, tokens, passwords, connection strings). Replace with `[REDACTED]` and
mention the redaction in the completion block.

## HTML Escaping in Generated Text

Quiz and diagram labels are rendered via `innerHTML` (see explanation-script.js)
so intentional inline markup (`<code>`, `<em>`, `<strong>`) displays correctly.
Any diff-derived string dropped into that same text must be HTML-escaped
(`&`, `<`, `>` at minimum) before insertion. Hand-authored prose and deliberate
inline tags are exempt — only text copied from the diff needs escaping.
