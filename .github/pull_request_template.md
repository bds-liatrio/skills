<!--
PR Title Format: <type>(<optional scope>): <description>

Valid types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

Examples:
  feat(skills): add new aws-vpc-creator skill
  fix: correct frontmatter in work-breakdown
  docs: update install instructions

The PR title is validated automatically.
-->

## Why?

<!-- Summarize the motivation for this change. -->

## What Changed?

<!-- Call out the key updates (which skill(s) added/updated, tooling changes, etc.). -->

## Additional Notes

<!-- Optional: follow-ups, rollout concerns, or reviewer guidance. -->

- [ ] Ran validation: `make validate`
- [ ] Ran the full gate: `pre-commit run --all-files`
- [ ] New/updated skills have valid `SKILL.md` frontmatter (`name` + `description`)
- [ ] Verified discovery: `make verify-discovery`
