#!/usr/bin/env bash
#
# Install the bundled `linear-project-manager` sub-agent definition into an
# agent-definitions directory so the host harness can discover it.
#
# The sdd-linear skill delegates ALL Linear access to this sub-agent, so the
# agent must be registered wherever the harness reads agent definitions. This
# script is idempotent and non-destructive: it skips an existing agent of the
# same name unless --force is given.
#
# Usage:
#   install-linear-agent.sh [--dest DIR] [--force]
#
#   --dest DIR   Target agent-definitions directory.
#                Default: $AGENTS_DIR, else ~/.agents/agents
#                (the canonical, vendor-neutral location many tools symlink to).
#                Other common targets: ~/.cursor/agents, ~/.claude/agents
#   --force      Overwrite an existing agent file of the same name.
#
# Output: `key=value` lines (src, target, status) for easy scripting.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="${script_dir}/../agents/linear-project-manager.md"

dest="${AGENTS_DIR:-${HOME}/.agents/agents}"
force=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dest)
      dest="${2:?--dest requires a directory argument}"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      sed -n '3,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ ! -f "$src" ]; then
  echo "error: bundled agent not found at: $src" >&2
  exit 1
fi

target="${dest%/}/linear-project-manager.md"
echo "src=${src}"
echo "target=${target}"

if [ -e "$target" ] && [ "$force" -ne 1 ]; then
  echo "status=exists"
  echo "note=an agent named linear-project-manager already exists; re-run with --force to overwrite" >&2
  exit 0
fi

mkdir -p "$dest"
cp "$src" "$target"

if [ "$force" -eq 1 ]; then
  echo "status=forced"
else
  echo "status=installed"
fi
