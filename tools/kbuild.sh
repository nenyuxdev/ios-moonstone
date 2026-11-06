#!/bin/sh
# One kernel build at a time on GitHub Actions, without waiting for GitHub to mark the run done.
#   tools/kbuild.sh NAME [LABEL="extra boot-args"]...
# Cancels runs still queued/running, dispatches xnu.yml for the pushed HEAD of the current branch,
# takes the xnu-kernel artifact as soon as it exists (~6 min; GitHub can show the run "in progress"
# for a while after the job ended), then builds out/boot-NAME-LABEL.img per LABEL with tools/mkboot.sh
# (Moonstone kernel-entry profile; no userspace, root mount, or GPU initialization.)
set -eu
cd "$(dirname "$0")/.."
name=${1:?usage: kbuild.sh NAME [LABEL="boot-args"]...}; shift
repo=$(git remote get-url origin | sed -E 's#^(git@github.com:|https://github.com/)##; s#\.git$##')
branch=$(git rev-parse --abbrev-ref HEAD)
base="debug=0xc cpus=1 keepsyms=1 -noprogress wdt=-1"
head=$(git rev-parse HEAD)
[ "$(git rev-parse "origin/$branch")" = "$head" ] || { echo "push $branch first" >&2; exit 1; }

for r in $(gh run list -R "$repo" -w xnu.yml -L 20 --json databaseId,status -q ".[]|select(.status!=\"completed\")|.databaseId"); do
  gh run cancel -R "$repo" "$r" >/dev/null 2>&1 || true
done
t0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
gh workflow run xnu.yml -R "$repo" --ref "$branch"
run=""
for i in $(seq 30); do
  sleep 4
  run=$(gh run list -R "$repo" -w xnu.yml -L 5 --json databaseId,headSha,createdAt -q ".[]|select(.headSha==\"$head\" and .createdAt>=\"$t0\")|.databaseId" | head -1)
  [ -n "$run" ] && break
done
[ -n "$run" ] || { echo "dispatched run not found" >&2; exit 1; }
echo "run $run (https://github.com/$repo/actions/runs/$run)"

for i in $(seq 120); do
  a=$(gh api "repos/$repo/actions/runs/$run/artifacts" -q ".artifacts[]|select(.name==\"xnu-kernel\")|.name" 2>/dev/null || true)
  [ -n "$a" ] && break
  c=$(gh api "repos/$repo/actions/runs/$run/jobs" -q ".jobs[0].conclusion" 2>/dev/null || true)
  if [ "$c" = failure ] || [ "$c" = cancelled ]; then
    echo "build $c" >&2
    gh run view -R "$repo" "$run" --log-failed 2>/dev/null | grep -E "[0-9]+: error:" | head -20 >&2 || true
    exit 1
  fi
  sleep 15
done
[ -n "$a" ] || { echo "no artifact after 30 min" >&2; exit 1; }
k=xnu/out-$name
rm -rf "$k"; mkdir -p "$k"
gh run download -R "$repo" "$run" -n xnu-kernel -D "$k"
for v in "$@"; do
  label=${v%%=*}; extra=${v#*=}
  # Keep the packer's failure status: a pipeline ending in tail would hide it in sh.
  packed=$(CMDLINE="$base $extra" tools/mkboot.sh "$k/kernel.development.moonstone" "out/moonstone-$name-$label.img")
  printf '%s\n' "$packed" | tail -2
done
