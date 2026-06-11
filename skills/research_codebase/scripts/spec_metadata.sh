#!/usr/bin/env bash
# spec_metadata.sh - print metadata for a research document's frontmatter.
#
# Self-contained helper bundled with the research_codebase skill. Works in any
# git repository, including jj-colocated repos (which are git repos underneath).
# All git lookups are best-effort: missing values come back empty rather than
# failing the whole run.
set -euo pipefail

iso_date="$(date +%Y-%m-%dT%H:%M:%S%z)"
short_date="$(date +%Y-%m-%d)"

researcher="$(git config user.name 2>/dev/null || true)"
[ -n "${researcher}" ] || researcher="$(whoami 2>/dev/null || echo "unknown")"

commit="$(git rev-parse HEAD 2>/dev/null || echo "")"

# Branch name. `symbolic-ref` gives the checked-out branch; when HEAD is
# detached (e.g. jj-colocated repos) fall back to a branch ref that points at
# HEAD, otherwise report it honestly as detached rather than the literal "HEAD".
branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [ -z "${branch}" ]; then
  branch="$(git for-each-ref --points-at HEAD --count=1 --format='%(refname:short)' refs/heads 2>/dev/null || true)"
fi
[ -n "${branch}" ] || branch="(detached)"

url="$(git config --get remote.origin.url 2>/dev/null || true)"
repo=""
if [ -n "${url}" ]; then
  repo="$(basename "${url}")"
  repo="${repo%.git}"
fi
if [ -z "${repo}" ]; then
  top="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  repo="$(basename "${top}")"
fi

cat <<EOF
date: ${iso_date}
researcher: ${researcher}
git_commit: ${commit}
branch: ${branch}
repository: ${repo}
last_updated: ${short_date}
last_updated_by: ${researcher}
EOF
