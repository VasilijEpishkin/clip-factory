#!/usr/bin/env bash
# Gemini bridge watcher: sync Drive <-> <repo>/gemini-bridge, run an agent only when Gemini wrote something new.
# Usage: scripts/bridge_poll.sh        (BRIDGE_AGENT=claude|codex|hermes|none, default claude)
set -euo pipefail

RC=${RCLONE:-$HOME/.local/bin/rclone}
REPO=$(cd "$(dirname "$0")/.." && pwd)
DIR=${BRIDGE_DIR:-$REPO/gemini-bridge}
AGENT=${BRIDGE_AGENT:-claude}
STATE=$DIR/.last_seen
mkdir -p "$DIR"
exec 9>"$DIR/.lock"; flock -n 9 || exit 0   # one poll at a time

# Docs -> txt so agents read plain text; ".gdoc" shortcuts are not created.
RC_OPTS=(--drive-export-formats txt --drive-skip-gdocs=false --exclude ".*")

# 1. pull everything (copy: never deletes locally)
"$RC" copy "gdrive:" "$DIR" "${RC_OPTS[@]}" -q

# 2. push agent-owned files only (requests, reviews, briefs, refs, final, archive)
for p in "$DIR"/projects/*/; do
  n=$(basename "$p")
  for d in requests reviews 01_to_gemini 03_final _archive; do
    [ -d "$p$d" ] && "$RC" copy "$p$d" "gdrive:projects/$n/$d" -q
  done
  [ -f "$p/brief.md" ] && "$RC" copyto "$p/brief.md" "gdrive:projects/$n/brief.md" -q
done

# 3. fingerprint of Gemini-owned output; no change -> no agent, no tokens
cur=$(cd "$DIR" && find projects -path '*/results/*' -o -path '*/02_from_gemini/*' -type f -printf '%p %s %T@\n' 2>/dev/null | sort | sha256sum | cut -d' ' -f1)
[ -f "$STATE" ] && [ "$(cat "$STATE")" = "$cur" ] && exit 0
echo "$(date -Is) change detected, agent=$AGENT"

PROMPT='Follow docs/gemini-bridge.md "Agent side": run one poll. Drive is synced locally at gemini-bridge/ in the repo (read results/ and 02_from_gemini there, write reviews/ and requests/ there; scripts/bridge_poll.sh uploads them). Report what changed in one line.'
cd "$REPO"
case $AGENT in
  claude) claude -p "$PROMPT" ;;
  codex)  codex exec "$PROMPT" ;;
  hermes) HERMES_HOME=${CLIP_HERMES_HOME:-$HOME/.hermes} hermes -z "$PROMPT" ;;
  none)   ;;
esac
echo "$cur" > "$STATE"
# push reviews/requests the agent just wrote
"$RC" copy "$DIR" "gdrive:" "${RC_OPTS[@]}" --exclude "**/results/**" --exclude "**/02_from_gemini/**" -q --max-age 1h
