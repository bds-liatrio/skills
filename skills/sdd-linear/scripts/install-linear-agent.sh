#!/usr/bin/env bash
#
# Install the bundled `linear-project-manager` sub-agent definition into an
# agent-definitions directory so the host harness can discover and invoke it
# *by name* (e.g. `/linear-project-manager`).
#
# The sdd-linear skill delegates ALL Linear access to this sub-agent, so the
# agent must live wherever the harness reads agent definitions. This script is
# idempotent and non-destructive: it skips an existing agent of the same name
# unless --force is given.
#
# Usage:
#   install-linear-agent.sh [--dest DIR] [--force]
#
#   --dest DIR   Install into exactly this agent-definitions directory.
#                Without --dest, the script uses $AGENTS_DIR if set, otherwise
#                auto-detects installed harness user-agent dirs
#                (~/.cursor/agents, ~/.claude/agents, ~/.codex/agents) and
#                installs into each whose harness is present. If none are found
#                it creates and installs into ~/.cursor/agents.
#                NOTE: the vendor-neutral ~/.agents/agents is NOT read by these
#                harnesses unless it is symlinked into one of the dirs above.
#   --force      Overwrite an existing agent file of the same name.
#
# Output: `key=value` lines (src once, then a target/status pair per
# destination) for easy scripting.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="${script_dir}/../agents/linear-project-manager.md"

dest=""
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
      sed -n '3,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

echo "src=${src}"

install_one() {
  dir="$1"
  target="${dir%/}/linear-project-manager.md"
  echo "target=${target}"
  if [ -e "$target" ] && [ "$force" -ne 1 ]; then
    echo "status=exists"
    echo "note=an agent named linear-project-manager already exists at ${target}; re-run with --force to overwrite" >&2
    return 0
  fi
  mkdir -p "$dir"
  cp "$src" "$target"
  if [ "$force" -eq 1 ]; then
    echo "status=forced"
  else
    echo "status=installed"
  fi
}

if [ -n "$dest" ]; then
  install_one "$dest"
elif [ -n "${AGENTS_DIR:-}" ]; then
  install_one "$AGENTS_DIR"
else
  installed_any=0
  for d in "${HOME}/.cursor/agents" "${HOME}/.claude/agents" "${HOME}/.codex/agents"; do
    # Install only where the harness is actually present (its config dir exists).
    if [ -d "$(dirname "$d")" ]; then
      install_one "$d"
      installed_any=1
    fi
  done
  if [ "$installed_any" -eq 0 ]; then
    install_one "${HOME}/.cursor/agents"
  fi
fi
