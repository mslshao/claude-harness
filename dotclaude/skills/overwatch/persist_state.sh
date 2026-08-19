#!/usr/bin/env bash
# Usage: persist_state.sh <bead-id> <cycle-result-json-path>
# Extracts .blob from a cycle.py result file and persists it via the safe
# script-file pattern (avoids block-bd-computed-field-write.sh on a
# shell-substituted --notes value). See SKILL.md Step 5.
set -euo pipefail
bead_id="$1"
result_file="$2"
blob_file="$(mktemp)"
cmd_file="$(mktemp)"
python3 -c "
import json
d = json.load(open('$result_file'))
with open('$blob_file', 'w') as f:
    json.dump(d['blob'], f)
"
if grep -q "'" "$blob_file"; then
  echo "ERROR: blob contains an unescaped single quote; state JSON should never legitimately have one" >&2
  exit 1
fi
python3 -c "
content = open('$blob_file').read()
with open('$cmd_file', 'w') as f:
    f.write('bd update $bead_id --notes \'' + content + '\'\n')
"
bash "$cmd_file"
