#!/usr/bin/env bash
# scrub-check.sh: CI guardrail for the personalized Claude Code harness repo.
#
# Scans repo content for patterns that should have been scrubbed before commit.
# Exits 1 on any finding. Exits 0 on clean.
#
# Spec: see sync/SCRUB-SPEC.md for what gets scrubbed and why.
#
# Tier 1 (real names) reads its pattern list from the gitignored local file
# sync/scrub-names.local so the committed repo carries no real names, not
# even inside its own detector. When that file is absent or has no patterns,
# Tier 1 is SKIPPED with a loud stderr warning and a qualified summary line;
# Tiers 2-4 still run, and the script never prints an unqualified "clean"
# for a scan it did not perform. Fail-open-with-loud-warning mirrors the
# jq-missing philosophy in the harness's enforcement hooks.

set -euo pipefail

# Anchor to the script's own location so the check runs against THIS repo
# regardless of the caller's cwd. The script lives in <repo>/sync/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -d "$REPO_ROOT/.git" ]; then
  echo "scrub-check: expected $REPO_ROOT to be a git repo root" >&2
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

# Always include top-level Markdown files in the scan.
SCAN_FILES=(README.md WORLDMAP.md)

# Tier 1: real names of teammates. The pattern list is externalized to the
# gitignored sync/scrub-names.local (one extended-regex pattern per line;
# '#' comments and blank lines ignored; patterns are OR-joined). The list
# stays out of the commit so the committed repo is name-free; tweak the
# local file as team composition changes. Absent-file behavior is documented
# in the header above.
NAMES_FILE="$SCRIPT_DIR/scrub-names.local"
TIER1_NAMES_REGEX=""
if [ -f "$NAMES_FILE" ]; then
  TIER1_NAMES_REGEX="$(grep -vE '^[[:space:]]*(#|$)' "$NAMES_FILE" 2>/dev/null | paste -sd'|' - || true)"
fi

# Tier 2: incident-specific patterns + employer identification.
# The repo refers to the employer's actual GitHub org and codebase paths
# using generic placeholders (lawfirm/main, /workspaces/main). Any reversion
# to the real identifiers signals a regression and gets caught here.
TIER2_PATTERNS=(
  'Anthropic.*[Rr]ejection'
  'Anthropic.*technical enablement'
  'rejected.*from Anthropic'
  '<company>'
  '\bM&M\b'
  '/workspaces/main\b'
  '-workspaces-main\b'
)

# Tier 3: internal tracking IDs.
# Notes:
# - Bead IDs (docr-XXXX) stay as authentic operational flavor. They tie
#   calibration entries to specific historical instances; public readers
#   see them as opaque references but the principle around them still reads.
# - AWS resource names beginning with the workspace prefix (docr-deployment,
#   docr-dev-deployment) are Tier 4 infrastructure detail; allowed.
TIER3_PATTERNS=(
  '<confluence-space-id>'               # confluence space ID
  '<atlassian-cloud-id>'                 # atlassian cloud ID
  '\bMX2-[0-9]+\b'                                       # specific Jira ticket numbers (placeholder forms MX2-XXXXX/NNNNN do not match)
)

# Tier 4: infrastructure detail patterns (cautious; many of these will be
# legitimate examples in unscrubbed contexts; this list is starter-shaped).
TIER4_PATTERNS=(
  'dyn-<service>-.*-dlq'                                    # specific queue names
  'arn:aws:.*:.*:.*'                                     # AWS ARNs identify
  '\bQuaero\b'                                           # internal service name (capital, prose contexts)
  '\bquaero\b'                                           # internal service name (lowercase, identifier contexts)
  'morgan\.atlassian\.net'                               # team's Atlassian instance hostname
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

TIER1_SKIPPED=0
if [ -n "$TIER1_NAMES_REGEX" ]; then
  scan_pattern "1 (real names)" "$TIER1_NAMES_REGEX"
else
  TIER1_SKIPPED=1
  echo "scrub-check: WARNING: $NAMES_FILE not found (or contains no patterns)." >&2
  echo "scrub-check: WARNING: Tier 1 real-name scan DISABLED; create it to enable. See sync/SCRUB-SPEC.md Tier 1." >&2
fi

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
  if [ "$TIER1_SKIPPED" -eq 1 ]; then
    echo "scrub-check: Tiers 2-4 clean (${#SCAN_FILE_LIST[@]} files scanned, 0 findings); Tier 1 real-name scan SKIPPED (no scrub-names.local)"
  else
    echo "scrub-check: clean (${#SCAN_FILE_LIST[@]} files scanned, 0 findings)"
  fi
  exit 0
else
  echo "scrub-check: $FINDINGS pattern hit(s). See sync/SCRUB-SPEC.md for what to do."
  exit 1
fi
