---
name: jj-case-insensitive-clone-fix
description: 'Diagnose and fix the "Failed to update refs:" error from `jj git clone` (and the bundled `jj-clone` wrapper script) on case-insensitive filesystems like macOS APFS. Use when a `jj` clone fails with `Error: Failed to update refs: refs/remotes/origin/<name>`, when remote refs differ only in case, or when investigating ref-update failures from gitoxide. Knows why the standard `git refs migrate --ref-format=reftable` workaround does NOT work for jj-managed repos.'
---

# Cloning with jj on Case-Insensitive Filesystems

## When this applies

`jj git clone` (or the bundled `jj-clone` wrapper) fails with output like:

```
Fetching into new repo in "..."
git: warning: no common commits
remote: Enumerating objects: ...
Error: Failed to update refs: refs/remotes/origin/<some-ref-name>
```

The named ref is one half of a case-collision pair on the remote
(e.g. `MergeMasterToDevelop` vs `MergeMastertoDevelop`).

## Root cause

- macOS APFS (and any case-insensitive FS) treats `Foo` and `foo` as the same path.
- Git's default `files` ref backend stores each ref as a file under `.git/refs/...`.
- If the remote has two refs that differ only in case, the second clobbers the first → `Failed to update refs:`.
- `jj git clone` uses gitoxide, which has the same constraint as git's `files` backend.

Confirm the diagnosis with:

```bash
git ls-remote --heads <url> \
  | awk '{ sub(/^refs\/heads\//, "", $2); print $2 }' \
  | sort -f | uniq -d -i
```

A non-empty result means there are case-only collisions.

## Why `reftable` is NOT a solution for jj

The standard Git remediation is to switch to the `reftable` backend (binary file, no per-ref filesystem path):

```bash
git refs migrate --ref-format=reftable
# or for a fresh clone:
GIT_DEFAULT_REF_FORMAT=reftable git clone <url>
```

That works for `git`, but **gitoxide does not yet support reftable**
([gix issue #109](https://github.com/GitoxideLabs/gitoxide/issues/109)).
After cloning into a reftable repo:

- `jj git init --colocate` "succeeds" but imports zero bookmarks.
- `jj bookmark list -a` shows nothing; `jj log -r 'remote_bookmarks()'` is empty.
- `jj git fetch` reports "Nothing changed."

Do NOT recommend reftable for jj users. Do NOT recommend
`GIT_DEFAULT_REF_FORMAT=reftable jj git clone ...` — gitoxide
ignores it for ref reads anyway.

## The fix: exclude the case-colliding duplicates

Pick one ref to keep from each case-collision group, then fetch with
a negative refspec that skips the duplicates.

### Preferred: use the bundled `scripts/jj-clone`

This skill ships a `jj-clone` wrapper at [`scripts/jj-clone`](scripts/jj-clone)
that already implements this fallback: it tries `jj git clone`, detects
`Failed to update refs:` in the output, computes excludes from
`git ls-remote --heads`, and falls back to `git fetch` +
`jj git init --colocate`.

```bash
# From the skill directory, or with the script on your PATH:
scripts/jj-clone <git-url>
scripts/jj-clone -b ~/src <git-url>   # override the clone base dir
```

If a clone failed with `jj git clone` directly, just re-run
`scripts/jj-clone <url>`. An empty target directory left over from the
failed attempt is fine — the wrapper reuses it. The relevant function in
the script is `fallback_clone`.

### Manual remediation (no wrapper)

```bash
URL=<remote-url>
TARGET=<local-path>

# 1. List the case-only collisions on the remote.
EXCLUDES=$(
  git ls-remote --heads "$URL" \
    | awk '{ sub(/^refs\/heads\//, "", $2); print $2 }' \
    | awk '
        { key = tolower($0)
          if (key in first) print $0
          else first[key] = $0
        }'
)
# $EXCLUDES is the branch names to drop (one per collision group;
# keeps the lexicographically first-seen ref).

# 2. Pre-create the repo with the files backend.
#    Belt-and-suspenders: unset the env var AND pass --ref-format=files.
mkdir -p "$TARGET" && cd "$TARGET"
unset GIT_DEFAULT_REF_FORMAT
git init --ref-format=files --initial-branch=main
git remote add origin "$URL"

# 3. Configure refspec: fetch all heads, except the duplicates.
git config --replace-all remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
for ex in $EXCLUDES; do
  git config --add remote.origin.fetch "^refs/heads/$ex"
done

# 4. Fetch, then layer jj on top.
git fetch origin
jj git init --colocate
```

## Verification

After remediation, confirm the repo is fully usable from jj:

```bash
git config extensions.refStorage      # must be UNSET (i.e. files), not `reftable`
jj log -r 'trunk()' --no-graph        # should resolve to master/main
jj bookmark list -a | head            # should list imported bookmarks
```

If `extensions.refStorage` prints `reftable`, jj cannot read the repo —
start over with `git init --ref-format=files`.

## Trade-offs to surface to the user

- Excluded refs are not fetchable later; they're encoded as
  `^refs/heads/<name>` in `.git/config`. To grab one, drop that
  negative refspec or add a one-off named refspec (e.g.
  `+refs/heads/MergeMastertoDevelop:refs/remotes/origin/MergeMastertoDevelop_lc`).
- The picker is deterministic (lexicographic first wins) but
  arbitrary across collision pairs. Fine for stale merge branches;
  worth flagging if both halves of a collision look active.
- Detection is failure-driven on purpose. Don't add an upfront
  `git ls-remote` to every clone — it adds a network roundtrip to
  the healthy path.

## Anti-patterns

- Don't recommend `git refs migrate --ref-format=reftable` for jj-managed repos.
- Don't suggest creating a case-sensitive APFS volume just for one repo unless the user explicitly asks.
- Don't `rm -rf` the target dir without checking — an empty dir from a failed `jj git clone` is reusable.
- Don't rely on `GIT_DEFAULT_REF_FORMAT` reaching jj/gitoxide; it doesn't.

## References

- gitoxide reftable tracking issue: https://github.com/GitoxideLabs/gitoxide/issues/109
- jj clone-on-case-insensitive FS issue: https://github.com/jj-vcs/jj/issues/9040
- Bundled wrapper script: [`scripts/jj-clone`](scripts/jj-clone)
