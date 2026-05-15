#!/usr/bin/env bash
# scrub-check.sh: CI guardrail for the personalized Claude Code harness repo.
#
# Scans repo content for patterns that should have been scrubbed before commit.
# Exits 1 on any finding. Exits 0 on clean.
#
# Spec: see sync/SCRUB-SPEC.md for what gets scrubbed and why.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
  echo "scrub-check: not inside a git repo" >&2
  exit 2
fi

cd "$REPO_ROOT"

# Directories to scan. learnings/ and .git/ and sync/ are excluded by design.
SCAN_DIRS=(
  patterns
  dispatch
  scaffolding
  dotclaude
  project-tier
  graveyard
  evidence
)

# Always include the top-level README in the scan.
SCAN_FILES=(README.md)

# Tier 1: real names of teammates (first names only; first+last would be more
# precise but more false-positive prone since 'a team lead manager' or 'a teammate' is generic).
# Word-boundary required to avoid false positives ('davidson', 'a peer reviewer' inside
# 'atomic', etc.). Tweak this list as the team composition changes.
TIER1_NAMES_REGEX='\b(the engineering lead|a team lead|a teammate|a peer reviewer|a solo-team engineer|a teammate|a teammate|a teammate)\b'

# Tier 2: incident-specific patterns.
TIER2_PATTERNS=(
  'Anthropic.*[Rr]ejection'
  'Anthropic.*technical enablement'
  'rejected.*from Anthropic'
)

# Tier 3: internal tracking IDs.
TIER3_PATTERNS=(
  '\bdocr-[a-z0-9]{4,}\b'                                # bead IDs
  '\bMX2-[0-9]{4,6}\b'                                   # Jira ticket numbers
  '<confluence-space-id>'               # confluence space ID
  '<atlassian-cloud-id>'                 # atlassian cloud ID
)

# Tier 4: infrastructure detail patterns (cautious; many of these will be
# legitimate examples in unscrubbed contexts; this list is starter-shaped).
TIER4_PATTERNS=(
  'dyn-<service>-.*-dlq'                                    # specific queue names
  'arn:aws:.*:.*:.*'                                     # AWS ARNs identify
)

FINDINGS=0

# Build the list of files to scan once.
mapfile -t SCAN_FILE_LIST < <(
  for d in "${SCAN_DIRS[@]}"; do
    if [ -d "$d" ]; then
      find "$d" -type f \( -name '*.md' -o -name '*.sh' -o -name '*.py' -o -name '*.yml' -o -name '*.yaml' -o -name '*.toml' \)
    fi
  done
  for f in "${SCAN_FILES[@]}"; do
    [ -f "$f" ] && echo "$f"
  done
)

if [ ${#SCAN_FILE_LIST[@]} -eq 0 ]; then
  echo "scrub-check: no files matched the scan glob (clean repo?)"
  exit 0
fi

scan_pattern() {
  local tier="$1"
  local pattern="$2"
  local hits
  # -E for extended regex, -n for line numbers, -H for filename, -I to skip binaries.
  hits=$(grep -EnHI "$pattern" "${SCAN_FILE_LIST[@]}" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo ""
    echo "=== Tier $tier finding: $pattern ==="
    echo "$hits"
    FINDINGS=$((FINDINGS + 1))
  fi
}

scan_pattern "1 (real names)" "$TIER1_NAMES_REGEX"

for p in "${TIER2_PATTERNS[@]}"; do
  scan_pattern "2 (incident reference)" "$p"
done

for p in "${TIER3_PATTERNS[@]}"; do
  scan_pattern "3 (internal tracking)" "$p"
done

for p in "${TIER4_PATTERNS[@]}"; do
  scan_pattern "4 (infrastructure detail)" "$p"
done

echo ""
if [ "$FINDINGS" -eq 0 ]; then
  echo "scrub-check: clean (${#SCAN_FILE_LIST[@]} files scanned, 0 findings)"
  exit 0
else
  echo "scrub-check: $FINDINGS pattern hit(s). See sync/SCRUB-SPEC.md for what to do."
  exit 1
fi
