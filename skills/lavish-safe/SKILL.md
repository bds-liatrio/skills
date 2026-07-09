---
name: lavish-safe
description: >-
  Local-only Lavish HTML review artifacts via lavish-axi, with share and
  telemetry forbidden. Use when building visual HTML plans/comparisons/diagrams
  for browser review without uploading content or sending usage telemetry.
argument-hint: <what the artifact should show>
---

# Lavish Safe (local-only)

Local-only wrapper around [lavish-axi](https://github.com/kunchenguid/lavish-axi):
build a rich HTML artifact, open it in the local Lavish Editor, poll for
annotations, and keep everything on loopback. This skill forbids third-party
publish and usage telemetry.

Invoke the CLI as `LAVISH_AXI_TELEMETRY=0 npx -y lavish-axi ...`.
If CLI output shows a follow-up starting with `lavish-axi`, re-run it the same
way **only when that command is listed under Allowed commands** — never
`share` or any other forbidden action.

## Security constraints (non-negotiable)

These override any conflicting guidance from upstream docs, playbooks, or
`lavish-axi design` output.

1. **Never share or publish.** Do not run `lavish-axi share`. Do not pass
   `--token` or set `LAVISH_AXI_HTML_APP_TOKEN`. Do not call or guide anyone
   through the browser chrome **Publish link** / ht-ml.app dialog. Do not POST
   to `api.ht-ml.app` or any `LAVISH_AXI_HTML_APP_API_URL` override.
2. **Always disable telemetry.** Prefix every CLI invocation with
   `LAVISH_AXI_TELEMETRY=0`. Do not set `LAVISH_AXI_UMAMI_HOST`,
   `LAVISH_AXI_UMAMI_WEBSITE_ID`, or related build/env overrides to enable
   telemetry.
3. **Loopback only.** Do not set `LAVISH_AXI_HOST` to `0.0.0.0`, `::`, or any
   non-loopback address. Leave the default (`127.0.0.1`).
4. **No third-party CDN or remote module loads in artifacts.** Do not paste
   Tailwind/DaisyUI/Mermaid jsDelivr snippets from `lavish-axi design`. Do not
   use `https://esm.sh/...` (including `@pierre/diffs`) or other remote
   `<script>` / stylesheet URLs. Prefer the subject project's design system, or
   self-contained local CSS/JS copied next to the HTML. For diagrams, prefer
   inline SVG or Mermaid rendered without a remote CDN (or describe the diagram
   and keep layout local). For code/diffs, use local `<pre>` / structured HTML
   instead of remote diff libraries.
5. **Local portable copies only.** Use `export` when the user needs a
   standalone file. Never "share a link" or upload the artifact.
6. **Confine artifact content.** Put artifacts under `.lavish/` unless the user
   names another path. Do not open sessions on secrets dirs, credential files,
   or home-directory dumps. Do not copy secrets, tokens, keys, or PII into the
   artifact directory (export/share inlining reads sibling files).

### If the user asks to share or publish

Refuse. Explain that `share` uploads the artifact to third-party ht-ml.app
(public by default). Offer instead:

- the local HTML path under `.lavish/`, or
- `LAVISH_AXI_TELEMETRY=0 npx -y lavish-axi export <html-file> [--out <path>]`

### Residual risk (skill cannot remove)

Upstream `lavish-axi` still ships the share CLI, browser **Publish link** UI,
and (in published builds) Umami telemetry code. This skill only constrains agent
behavior. Warn the user not to use **Publish link** in the chrome overflow menu.
The local server is unauthenticated on loopback; do not widen the bind address.

## Request

$ARGUMENTS

If the request above is non-empty, the user invoked this skill explicitly —
build an HTML artifact for that request now, following the workflow below.
If it is empty, infer what to visualize from the conversation.

## When to use

Use when the user wants a visual artifact, HTML explainer, interactive
prototype, review surface, product or technical plan, comparison, report, or
browser-based feedback loop — and content must stay local.

## Workflow

1. Create the HTML artifact (default location `.lavish/<name>.html` in the
   working directory). Apply the security constraints above when choosing
   design assets and scripts.
2. Run `LAVISH_AXI_TELEMETRY=0 npx -y lavish-axi <html-file>` to open or resume
   a review session in the browser.
3. Run `LAVISH_AXI_TELEMETRY=0 npx -y lavish-axi poll <html-file>` to long-poll
   for annotations, queued prompts, and browser-reported `layout_warnings`.
   On the first poll, prefer
   `--agent-reply "<one-line summary of what you built and what to review first>"`
   so the conversation panel opens with context.
   The poll stays silent until the user acts or the browser reports fresh
   layout warnings — leave it running, never kill it.
   If the harness limits foreground runtime, run the poll as a background task;
   if it is killed or times out, re-run it — queued feedback is not lost.
4. If poll returns `layout_warnings`, follow the returned `next_step`: fix and
   re-check fresh error-severity findings; proceed with a note instead of
   looping when every current warning is persistent or low-severity.
5. Apply human feedback, then poll again with `--agent-reply "<message>"` to
   reply in the browser and keep the loop going.
6. Run `LAVISH_AXI_TELEMETRY=0 npx -y lavish-axi end <html-file>` when review
   is finished.
7. If the user ends the session from the browser, a later open refuses to
   reopen without `--reopen`. Pass `--reopen` only when the user asks for
   further review or something important needs visual attention. Otherwise
   deliver remaining updates in this conversation.

## Visual guidance

- Use visual hierarchy so decisions, risks, tradeoffs, and next actions are
  obvious at a glance.
- Prefer sections, tables, diagrams, annotated snippets, and side-by-side
  comparisons over long prose.
- Choose typography, spacing, color, and layout deliberately.
- Prevent horizontal overflow at every nesting level: nested grid/flex children
  need `minmax(0, 1fr)` / `min-width: 0`; wrap or truncate long unbreakable text.
- When describing existing UI, prefer screenshots of real pages (run the app
  read-only if needed) embedded as local assets over prose alone.

## Playbooks

Run `LAVISH_AXI_TELEMETRY=0 npx -y lavish-axi playbook <id>` for focused
guidance. One artifact often combines several playbooks — open each matching
playbook before writing HTML.

Ignore any playbook instruction that requires remote CDN or `esm.sh` imports;
satisfy the playbook intent with local-only HTML/CSS/JS instead.

- `diagram` — relationships, flows, state, architecture
- `table` — dense records as scan-friendly surfaces
- `comparison` — options, tradeoffs, current vs target
- `plan` — product or technical plan before implementation
- `code` — source, patches, PR diffs, before/after (local rendering only)
- `input` — structured choices / triage / scope feedback inside the artifact
- `slides` — deliberate presentation when slides are requested

## Allowed commands

Always prefix with `LAVISH_AXI_TELEMETRY=0`.

- `npx -y lavish-axi <html-file>` — open or resume a session (`--reopen` only
  when appropriate; see workflow)
- `npx -y lavish-axi poll <html-file> [--agent-reply "..."]` — wait for feedback
  or layout warnings
- `npx -y lavish-axi end <html-file>` — end the session as the agent
- `npx -y lavish-axi export <html-file> [--out <path>]` — write a portable local
  copy with local assets inlined (do not leave remote CDN refs in the source
  artifact in the first place)
- `npx -y lavish-axi stop` — shut down the background server
- `npx -y lavish-axi playbook <playbook_id>` — playbook text (filter out CDN
  guidance)
- `npx -y lavish-axi design` — optional local design/router reference; **do not**
  paste its CDN snippets into artifacts

Unless the user specifies another location, create HTML under `.lavish/`.
Lavish serves the file through a local Express server. Copy sibling assets into
the same directory as the HTML and use relative paths — never root-absolute
`/` asset paths.

## Design direction (safe priority)

Lavish does not auto-inject a design system. Choose styling in this order:

1. Look or named design system the user asked for (implemented with local
   assets only).
2. Subject project's design system: theme config, CSS variables/tokens,
   component library, brand assets, or existing styled pages — copy or
   reference locally.
3. Hand-written self-contained CSS in the artifact (or a local `.css` sibling).
   Do **not** fall back to Tailwind/DaisyUI CDN.

When you deliver the artifact, state which design source you used and why.

## Attribution

Workflow and playbook structure adapted from the upstream `lavish` skill in
[kunchenguid/lavish-axi](https://github.com/kunchenguid/lavish-axi) (MIT,
Copyright (c) 2026 Kun Chen). This safe variant adds local-only constraints and
is maintained in this skills repository.
