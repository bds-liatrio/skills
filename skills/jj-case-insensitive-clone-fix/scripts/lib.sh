#!/usr/bin/env bash
# lib.sh - shared, deterministic ref-name helpers for the
# jj-case-insensitive-clone-fix skill. Sourced by both `jj-clone` (to compute
# the fetch exclusion list) and `diagnose` (to report collisions). Keeping the
# case-folding logic in one place means both scripts agree on which refs
# collide and which one "wins".
#
# These functions all read short branch names (one per line) on stdin so they
# are trivially testable without a network or real case-colliding refs.
#
# This file is sourced, not executed. Both callers already run under
# `set -euo pipefail`; re-asserting it here keeps the option set explicit and
# consistent if the lib is ever sourced elsewhere.
set -euo pipefail

# normalize_heads: turn `git ls-remote --heads` output into short branch names.
normalize_heads() {
  awk '{ sub(/^refs\/heads\//, "", $2); print $2 }'
}

# excludes_from_names: print the names to EXCLUDE -- for each case-folded group
# the first-seen name is kept, every later one is printed (deterministic:
# lexicographic-by-input-order first wins).
excludes_from_names() {
  awk '
    {
      key = tolower($0)
      if (key in first) print $0
      else first[key] = $0
    }'
}

# collisions_from_names: print one line per case-collision group containing all
# the colliding names (space-separated). Prints nothing when there are no
# collisions, so callers can branch on whether output is empty.
collisions_from_names() {
  awk '
    {
      key = tolower($0)
      names[key] = (key in names ? names[key] " " $0 : $0)
      count[key]++
      if (!(key in seen)) { order[++n] = key; seen[key] = 1 }
    }
    END {
      for (i = 1; i <= n; i++) {
        k = order[i]
        if (count[k] > 1) print names[k]
      }
    }'
}
