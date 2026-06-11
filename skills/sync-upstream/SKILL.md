---
name: sync-upstream
description: Sync a forked repository's default branch with its upstream remote, using merge or rebase as appropriate. Use when the user says "sync upstream", "update from upstream", "pull upstream changes", "rebase on upstream", or wants to bring their fork up to date with the original repo.
disable-model-invocation: true
---

# Sync Upstream

Bring a forked repo's default branch up to date with the upstream remote, resolve conflicts, and optionally push.

## Prerequisites

- `jj` (preferred) or `git`
- `glab` CLI (for GitLab default-branch detection) or `gh` CLI (for GitHub)

## Workflow

### Step 1: Gather context with `scripts/sync-context`

Run the bundled script from inside the repo. It performs the deterministic
detection/classification that used to be done by hand: detect the VCS (jj or
git), locate the `upstream` remote, detect the default branch (GitLab `glab` →
GitHub `gh` → generic `git remote show` fallback), fetch that branch from
upstream, and classify the integration strategy.

```bash
scripts/sync-context
```

It prints `key=value` lines, e.g.:

```
vcs=git
upstream_remote=present
upstream_url=https://github.com/acme/fork.git
default_branch=main
default_branch_source=git
fork_only_commits=2
behind_commits=5
immutable_fork_commits=false
strategy=rebase
```

Read `strategy=` to decide how to integrate in Step 4:

| `strategy` | Meaning | Integrate via |
|------------|---------|---------------|
| `fast-forward` | No fork-only commits; local is behind or equal | Step 4 · Strategy A |
| `rebase` | Mutable fork-only commits only (your own work) | Step 4 · Strategy B |
| `merge` | Fork-only history includes immutable/shared commits | Step 4 · Strategy C |
| `unknown` | Default branch could not be determined | Investigate manually (see fallback) |

The script's only side effect is fetching the upstream default branch — the
same fetch the workflow needs anyway.

**git has no notion of immutable commits**, so it always reports `rebase` when
fork-only commits exist. If you know the fork-only history contains commits
shared with others (e.g. previously merged upstream, teammates' commits),
prefer Strategy C (merge) instead.

### Step 2: Handle a missing upstream remote

If the script prints `upstream_remote=absent` (exit code 1), ask the user for
the upstream URL, add it, then re-run `scripts/sync-context`:

```bash
# jj
jj git remote add upstream <url>

# git
git remote add upstream <url>
```

> **Manual fallback (if the script can't run).** Detect VCS with `jj root`;
> list remotes with `jj git remote list` / `git remote -v`; detect the default
> branch via `glab api projects/:id | jq -r '.default_branch'`,
> `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, or
> `git remote show upstream | sed -n 's/.*HEAD branch: //p'`; fetch it
> (`git fetch upstream "$DEFAULT_BRANCH"` / `jj git fetch --remote upstream --branch "$DEFAULT_BRANCH"`);
> then compare `upstream/$DEFAULT_BRANCH..$DEFAULT_BRANCH` to count fork-only
> commits and pick the strategy from the table above.

### Step 3: Preserve local working copy changes

If the working copy has uncommitted modifications, save them before integrating:

**jj:**
```bash
# Check for changes
jj diff --stat

# If non-empty, snapshot them into a named change
jj describe -m "WIP: local changes before upstream sync"
jj new
```

**git:**
```bash
git stash push -m "local changes before upstream sync"
```

### Step 4: Integrate

#### Strategy A: Fast-forward (no fork-only commits)

**jj:**
```bash
jj bookmark set "$DEFAULT_BRANCH" -r "${DEFAULT_BRANCH}@upstream"
```

If jj refuses with "backwards or sideways", use `--allow-backwards` — this is expected when the bookmark tracks a remote.

**git:**
```bash
git checkout "$DEFAULT_BRANCH"
git merge "upstream/$DEFAULT_BRANCH" --ff-only
```

#### Strategy B: Rebase (mutable fork-only commits)

**jj:**

Rebase only mutable descendants — never use `jj rebase -b @ -d …` when there are immutable ancestors between `@` and the destination:

```bash
jj rebase -r @ -d "$DEFAULT_BRANCH"
```

For a branch with multiple mutable commits:

```bash
jj rebase -s <first-mutable-commit> -d "$DEFAULT_BRANCH"
```

**git:**
```bash
git rebase "upstream/$DEFAULT_BRANCH"
```

#### Strategy C: Merge (immutable fork-only commits)

**jj:**
```bash
jj new "$DEFAULT_BRANCH" "${DEFAULT_BRANCH}@upstream" -m "chore: merge upstream/$DEFAULT_BRANCH into fork"
```

After resolving any conflicts (Step 5), move the bookmark forward:

```bash
jj bookmark set "$DEFAULT_BRANCH" -r @
jj new  # fresh working copy on top
```

**git:**
```bash
git checkout "$DEFAULT_BRANCH"
git merge "upstream/$DEFAULT_BRANCH" -m "chore: merge upstream/$DEFAULT_BRANCH into fork"
```

### Step 5: Resolve conflicts

After integration, check for conflicts:

**jj:**
```bash
jj status
jj resolve --list
```

**git:**
```bash
git status --short | grep '^UU'
```

**Resolution strategy — auto-resolve trivial, ask about non-trivial:**

1. List all conflicted files.
2. For each file, read the conflict markers.
3. If the conflict is trivial (e.g. image tags where the fork uses its own registry/naming, import ordering, whitespace, adjacent non-overlapping edits), resolve it automatically and note what was done.
4. If the conflict is non-trivial (both sides changed the same logic), present the conflict to the user with context from both sides and ask how to resolve.
5. After resolving each file:
   - **jj:** Simply edit the file — jj tracks the working copy automatically.
   - **git:** `git add <file>` after editing.
6. Once all conflicts are resolved:
   - **jj:** `jj status` to confirm clean state.
   - **git (rebase):** `git rebase --continue`.
   - **git (merge):** conflicts are resolved in-place, commit is ready.

### Step 6: Restore local working copy changes

If changes were saved in Step 3:

**jj:**

Find the saved WIP change and squash it into the working copy, or manually re-apply:

```bash
jj squash --from <wip-change-id> --into @
```

If the WIP change is empty (modifications were lost during integration), inform the user which files had local changes so they can re-apply.

**git:**
```bash
git stash pop
```

### Step 7: Confirm before pushing

Present a summary to the user and ask for confirmation before pushing:

```
Summary:
- Strategy: [fast-forward / rebase / merge]
- Upstream: <upstream-url>
- Branch: <DEFAULT_BRANCH>
- Conflicts resolved: <count> (list files)
- New commits to push: <count>

Push <DEFAULT_BRANCH> to origin?
```

Use the AskQuestion tool if available, otherwise ask conversationally. **Never push without explicit user confirmation.**

### Step 8: Push

Only after user confirms:

```bash
# jj
jj git push --bookmark "$DEFAULT_BRANCH"

# git
git push origin "$DEFAULT_BRANCH"
```

If the push is rejected (non-fast-forward), inform the user and ask whether to force-push. Never force-push without explicit confirmation.

## Error Recovery

| Scenario | Action |
|----------|--------|
| Fetch fails on ref conflicts | Retry with `--branch $DEFAULT_BRANCH` to fetch only the default branch |
| Rebase hits immutable commits | Abort (`jj undo`) and switch to merge strategy |
| Rebase produces too many conflicts | Offer to abort (`jj undo` / `git rebase --abort`) and suggest merge instead |
| Local working copy changes lost during integration | Report which files were modified so the user can re-apply |
| Upstream remote URL is wrong | `jj git remote remove upstream` / `git remote remove upstream`, then re-add |
| Push rejected after integration | Ask user whether to force-push; explain the risk |
