#!/usr/bin/env bash
# run_skill_evals.sh — drive skill-creator evals via Cursor agent.
#
# For each skill: create the next iteration workspace, launch one agent process
# per eval id in parallel (each process must spawn with_skill + without_skill
# sub-agents), wait, then run an aggregate agent. Default model is Sonnet 5.
#
# Usage:
#   run_skill_evals.sh                 # all skills with evals/evals.json
#   run_skill_evals.sh <skill> [...]   # named skills only
#
# Env:
#   MODEL              agent model (default: claude-sonnet-5-high)
#   SKILLS_DIR         override skills root for validate_evals.py (tests)
#   CURSOR_WORKSPACE   --workspace passed to agent (default: repo root)
#
# Compatible with macOS /bin/bash 3.2 (no mapfile).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

MODEL="${MODEL:-claude-sonnet-5-high}"
WORKSPACE="${CURSOR_WORKSPACE:-${ROOT}}"
VALIDATE=(uv run python scripts/validate_evals.py)

if [ "$#" -gt 0 ]; then
  skills="$*"
else
  skills="$("${VALIDATE[@]}" --list)"
fi

if [ -z "${skills}" ]; then
  echo "no skills with evals/evals.json found under skills/" >&2
  exit 1
fi

for skill in ${skills}; do
  if [ ! -d "skills/${skill}" ]; then
    echo "skills/${skill} does not exist" >&2
    exit 1
  fi
  if [ ! -f "skills/${skill}/evals/evals.json" ]; then
    echo "skills/${skill}/evals/evals.json missing — add evals or pick another skill" >&2
    exit 1
  fi
done

run_one_eval() {
  local skill="$1"
  local eval_id="$2"
  local iteration_dir="$3"
  local prompt
  prompt=$(
    cat <<EOF
Read and follow the skill-creator skill.

Run ONLY eval id=${eval_id} from skills/${skill}/evals/evals.json (ignore other evals).

Hard requirements for parallelism:
- Spawn the with_skill and without_skill (baseline) runs as TWO dedicated sub-agents in the SAME turn.
- Do not run them sequentially. Do not work the eval inline in the parent agent.

Workspace (already created): ${iteration_dir}
Write under: ${iteration_dir}/eval-${eval_id}-<name>/ with with_skill/ and without_skill/ (outputs/, transcript.md, timing.json, grading.json).
Also write eval_metadata.json for this eval.

After both sub-agents finish: capture timing, grade expectations for this eval only, then print a one-paragraph result for eval id=${eval_id} (pass/fail counts per config). Prefer printing over opening a browser viewer.
EOF
  )
  echo "=== evals: ${skill}#${eval_id} ==="
  agent -p --trust --force --model "${MODEL}" \
    --output-format stream-json --stream-partial-output \
    --workspace "${WORKSPACE}" \
    "${prompt}" \
    | uv run python scripts/agent_stream_text.py
}

aggregate_skill() {
  local skill="$1"
  local iteration_dir="$2"
  local prompt
  prompt=$(
    cat <<EOF
Read and follow the skill-creator skill.

Aggregate already-completed eval runs for skill '${skill}' in ${iteration_dir}.
Do not re-run evals. Grade any runs still missing grading.json, then run aggregate_benchmark for this iteration, and print a concise results summary: per-eval pass rates by configuration, notable failures, and the workspace path. Prefer printing over opening a browser viewer.
EOF
  )
  echo "=== aggregate: ${skill} ==="
  agent -p --trust --force --model "${MODEL}" \
    --output-format stream-json --stream-partial-output \
    --workspace "${WORKSPACE}" \
    "${prompt}" \
    | uv run python scripts/agent_stream_text.py
}

failed=0
for skill in ${skills}; do
  ws="skills/${skill}-workspace"
  mkdir -p "${ws}"
  next=1
  while [ -d "${ws}/iteration-${next}" ]; do
    next=$((next + 1))
  done
  iteration_dir="${ws}/iteration-${next}"
  mkdir -p "${iteration_dir}"
  echo "=== skill: ${skill} -> ${iteration_dir} (model=${MODEL}) ==="

  ids="$("${VALIDATE[@]}" --list-ids "${skill}")"
  if [ -z "${ids}" ]; then
    echo "${skill}: no eval ids found" >&2
    failed=1
    continue
  fi

  pids=""
  for eval_id in ${ids}; do
    (
      set -euo pipefail
      run_one_eval "${skill}" "${eval_id}" "${iteration_dir}"
    ) &
    pids="${pids} $!"
  done

  for pid in ${pids}; do
    if ! wait "${pid}"; then
      failed=1
    fi
  done

  if ! aggregate_skill "${skill}" "${iteration_dir}"; then
    failed=1
  fi
done

exit "${failed}"
