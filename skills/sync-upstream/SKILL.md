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

### Step 1: Detect VCS

Check if `jj root` succeeds. If yes, use jj. Otherwise fall back to git.

### Step 2: Ensure upstream remote exists

**jj:**
```bash
jj git remote list
```

**git:**
```bash
git remote -v
```

If no `upstream` remote exists, ask the user for the upstream URL and add it:

```bash
# jj
jj git remote add upstream <url>

# git
git remote add upstream <url>
```

### Step 3: Detect default branch

Try in order:

1. `glab api projects/:id | jq -r '.default_branch'` (GitLab — works when inside a glab-configured repo)
2. `gh repo view --json defaultBranchRef -q .defaultBranchRef.name` (GitHub)
3. `git remote show upstream | grep 'HEAD branch' | awk '{print $NF}'` (generic fallback)

Store the result (e.g. `master` or `main`) as `$DEFAULT_BRANCH`.

### Step 4: Fetch upstream

Fetch only the default branch to avoid ref-name conflicts from upstream branches:

```bash
# jj
jj git fetch --remote upstream --branch "$DEFAULT_BRANCH"

# git
git fetch upstream "$DEFAULT_BRANCH"
```

If the full fetch (`jj git fetch --remote upstream` / `git fetch upstream`) fails due to ref conflicts, fall back to the branch-scoped fetch above.

### Step 5: Determine integration strategy (merge vs rebase)

Before integrating, assess the relationship between the local and upstream default branches.

**jj — check for fork-only commits:**
```bash
jj log -r "ancestors($DEFAULT_BRANCH) ~ ancestors(${DEFAULT_BRANCH}@upstream)" --limit 5
```

**git:**
```bash
git log --oneline "upstream/$DEFAULT_BRANCH".."$DEFAULT_BRANCH" | head -5
```

**Decision:**

| Situation | Strategy |
|-----------|----------|
| No fork-only commits (local is behind or equal) | Fast-forward the bookmark/ref — no merge or rebase needed |
| Fork-only commits exist AND are all mutable (your own work) | Rebase onto upstream |
| Fork-only commits include immutable/shared commits (merged upstream before, team commits) | Merge upstream into the fork |

**How to detect immutable commits (jj):** If `jj rebase` fails with "Commit … is immutable", the commits are immutable. Prefer merge in this case — do not adjust immutability settings.

### Step 6: Preserve local working copy changes

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

### Step 7: Integrate

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

After resolving any conflicts (Step 8), move the bookmark forward:

```bash
jj bookmark set "$DEFAULT_BRANCH" -r @
jj new  # fresh working copy on top
```

**git:**
```bash
git checkout "$DEFAULT_BRANCH"
git merge "upstream/$DEFAULT_BRANCH" -m "chore: merge upstream/$DEFAULT_BRANCH into fork"
```

### Step 8: Resolve conflicts

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

### Step 9: Restore local working copy changes

If changes were saved in Step 6:

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

### Step 10: Confirm before pushing

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

### Step 11: Push

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
