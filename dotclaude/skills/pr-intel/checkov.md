# Checkov IaC Analysis

Adds a Checkov static-analysis pass for Terraform/HCL diffs as part of `/pr-intel`. Catches
structural IaC regressions (IAM blast-radius, S3 public access, missing encryption,
network exposure) that don't depend on reviewer judgment to dispatch. Complements
`mx2-devops-build-deploy` (which reviews HCL correctness and pattern fit) and
`mx2-security-auditor` (which reasons about blast radius and HIPAA/audit angle).

Status: experimental enhancement, personal-tier first per lab-to-production rule.
Tracked in bead `docr-kfjv`.

## When to invoke

Run Checkov when ALL of:
1. `has_terraform: true` (changed files match `*.tf` or `*.hcl`)
2. At least one `*.tf` file is net-new (not in `merge_base_freshness.stale_files`)
3. Mode is `default` or `--mine` (skip for `--quick`)

Skip when:
- All terraform files in the diff are already on main (pure rebase artifact)
- The PR's only IaC files are `.terraform.lock.hcl` or generated lockfiles

## How to invoke

Checkov is a Python CLI (`pip install checkov`). Verify availability before running:

```bash
command -v checkov >/dev/null 2>&1 || pip install --user checkov >/dev/null 2>&1
```

For each net-new Terraform file in the worktree, run:

```bash
checkov \
  --file "$WORKTREE_DIR/<path>" \
  --output json \
  --soft-fail \
  --skip-download \
  --framework terraform 2>/dev/null
```

Flags rationale:
- `--soft-fail`: never returns nonzero; we read findings from stdout
- `--skip-download`: don't fetch upstream policy updates; use local rules only
- `--framework terraform`: skip Dockerfile/Kubernetes/CloudFormation scanners (irrelevant)

**Do NOT pass `--quiet` with `--output json`** - the combination produces empty output
in Checkov 3.2.x. The banner is harmless in JSON mode; stderr captures the version
header, stdout has the structured findings.

The output is a list-of-results (one entry per framework runner). Parse the entry
where `check_type == "terraform"`. Example parse:

```python
import json
data = json.loads(stdout)
items = data if isinstance(data, list) else [data]
tf = next((d for d in items if d.get("check_type") == "terraform"), {})
failed = tf.get("results", {}).get("failed_checks", [])
```

**Module resolution caveat**: MX2's terragrunt-managed Terraform uses internal module
references (e.g., `source = "/module/sqs"`). Checkov can't resolve these without
running `terragrunt run-all init` first, which is too heavy for a per-PR check. The
practical consequence is that Checkov only scans leaf resources visible in the file;
cross-module flow is invisible. This is acceptable for the use case (catching
structural regressions in leaf-resource definitions: bucket ACLs, IAM statements,
security group rules) but DOES NOT replace `mx2-devops-build-deploy`'s module-aware
review.

## Line-range filter (load-bearing)

Checkov findings carry `file_line_range = [start, end]` pointing at the resource block
in the post-image file. A file can appear in the PR's changeset (so file-presence
filtering passes) while the flagged resource is **pre-existing infrastructure**
untouched by the diff. Reporting those findings inline would attribute pre-existing
tech debt to the current PR, the same failure mode `synthesis.md` calls
"Pre-existing behavior attribution."

**Empirical validation 2026-05-11**: across 13 IaC PRs, file-only filtering produced
0 true positives and 2 false-positive PRs (8933 and 8934) flagging pre-existing
CloudWatch log groups. The line-range filter below brings that to 0 FP across the
same sample.

For each Checkov finding, drop it unless `file_line_range` overlaps with at least
one `+` hunk in the PR diff for the same file:

```python
def parse_plus_ranges(diff_for_file: str) -> list[tuple[int, int]]:
    """Extract post-image line ranges from `@@ -A,B +C,D @@` hunk headers."""
    import re
    ranges = []
    for line in diff_for_file.splitlines():
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            start = int(m.group(1))
            length = int(m.group(2)) if m.group(2) else 1
            if length > 0:
                ranges.append((start, start + length - 1))
    return ranges

def overlaps(finding_range: list[int], plus_ranges: list[tuple[int, int]]) -> bool:
    if not finding_range or len(finding_range) < 2:
        return False
    f_start, f_end = finding_range[0], finding_range[1]
    return any(f_start <= r_end and r_start <= f_end for r_start, r_end in plus_ranges)
```

Apply per-file:
```bash
# Get the +hunks for each .tf file
git -C "$WORKTREE_DIR" diff origin/main -- "<tf_path>"
```
Pass that diff text to `parse_plus_ranges`, then filter `failed_checks` by `overlaps`.

A finding survives the filter only when the diff actually modified lines inside the
flagged resource's range. New resources in net-new files will always overlap (the
entire file is in the +hunks). Edits to existing resources will overlap. Pre-existing
resources untouched by the diff will not.

**Exact-overlap edge case**: if a finding's `file_line_range` includes a `provider` or
`terraform { ... }` block that the PR touched only incidentally (e.g., bumping a
required_version), the line-range filter will surface that finding. Acceptable; the
reviewer can decide whether the version bump motivates the additional fix. The
alternative (whole-block matching) is too coarse.

**Helper script location**: `~/.claude/skills/pr-intel/checkov-filter.py`. Use as:
```bash
python3 ~/.claude/skills/pr-intel/checkov-filter.py \
  --checkov-json <path> \
  --diff <path> \
  --file <tf-path-relative-to-repo>
```
Outputs the filtered failed_checks as JSON. Exit code 0 always (Checkov findings,
even surviving ones, are advisory).

Parse the JSON output: `results.failed_checks` contains the findings. Each has:
- `check_id`: e.g., `CKV_AWS_111` (catalog: https://www.checkov.io/5.Policy%20Index/terraform.html)
- `check_name`: human-readable rule name
- `file_path`, `file_line_range`: location
- `severity`: usually `null` for built-in checks (Checkov doesn't ship severity by default)
- `description`: rule explanation
- `guideline`: link to remediation

## Mapping Checkov findings to FINDING format

Checkov findings flow through pr-intel's normal severity-triage. Apply this mapping
before passing to synthesis:

| Check category | pr-intel severity |
|----------------|-------------------|
| IAM wildcards, public S3 buckets, public RDS, open security groups | BLOCKING |
| Missing encryption at rest, missing CMK, missing TLS enforcement | DISCUSSION (high-consequence) |
| Missing tags, missing log retention, missing versioning | MINOR |
| Anything else not in the above buckets | DISCUSSION (low-consequence) |

Convert to FINDING block:

```
FINDING:
  file: <relative path from repo root>
  location: <resource block or module path>
  code: <verbatim line(s) at file_line_range>
  evidence: VERIFIED
  verification: Checkov rule <check_id> (<check_name>)
  issue: <check_name>
  impact: <description, abbreviated to one line>
  severity: BLOCKING | DISCUSSION | MINOR
  note_to_reviewer: <guideline URL>
```

Always `evidence: VERIFIED`. Checkov findings are structural matches, not heuristics.

## Calibration: noise suppression

The Checkov default ruleset is opinionated and flags patterns we accept. Suppress
these check IDs at parse time before passing to synthesis (drop the finding entirely):

| Check ID | Why suppressed |
|----------|----------------|
| `CKV_AWS_109` | Ensure IAM permits actions w/o conditions - too generic; many MX2 IAM roles intentionally use action-only grants for service roles |
| `CKV_AWS_111` | Ensure write access requires conditions - same rationale; MX2 dev/eng roles have wide write access by design |
| `CKV_AWS_115` | Ensure Lambda function-level concurrent execution limit - we manage this via terragrunt defaults, not per-resource |
| `CKV_AWS_116` | Ensure Lambda DLQ configured - we use SQS-on-failure routing, Checkov doesn't recognize the pattern |
| `CKV_AWS_117` | Ensure Lambda inside VPC - majority of MX2 Lambdas are intentionally outside VPC for cold-start latency |
| `CKV_AWS_173` | Ensure encrypted Lambda env vars - we use Secrets Manager references, not env-var-encrypted secrets |

This suppression list will grow as we run on real PRs. Add a check ID here only after
seeing it fire as a false positive on 2+ MX2 PRs.

## Output integration

Findings appear in pr-intel's standard flow:

1. **Specialist Dispatch (parallel)**: Checkov runs alongside the specialist agents.
   It's an inline tool call, not a subagent. Time budget: 5-10 seconds per file.
2. **Synthesis input**: parsed FINDING blocks are concatenated with specialist results.
3. **Briefing**: BLOCKING findings appear in Draft Inline Comments at the file:line
   range; DISCUSSION/MINOR findings either get inline comments or fold into the
   Draft Review Summary per the existing budget rules (see synthesis.md).
4. **Attribution**: every inline comment derived from Checkov includes the check ID
   and a one-line rule name so the author can suppress in `.checkov.yml` if disagreed.

Example inline comment text (BLOCKING):

```
This grants `iam:*` on a wildcard resource (`CKV_AWS_287`: ensure managed policies
don't grant IAM permissions on `*`). For broadly-scoped engineer roles, narrow the
action to the specific managed APIs you intend to expose, or scope the resource to
a path prefix.
```

The check ID at the end (`CKV_AWS_287`) lets the author either fix or document a
suppression rationale.

## What Checkov does NOT replace

- **`mx2-security-auditor`**: still dispatched when security/PII files are touched.
  Checkov flags structural IaC issues; security-auditor reasons about blast radius,
  HIPAA, and audit-trail completeness.
- **`mx2-devops-build-deploy`**: still dispatched on IaC PRs. Reviews pattern fit
  (module conventions, terragrunt dependency injection, environment-config
  completeness) that Checkov can't see.
- **Datadog IaC PR gate**: Datadog runs server-side on push. Checkov here runs
  locally in pr-intel for the briefing. The two are complementary; Datadog's
  detection is a CI gate, Checkov's is a reviewer-side check.

## First-run validation (recorded 2026-05-11)

Tested on PR #8995 (broadening of `dev/*` secrets on `mx2-swe` IAM role):

```
terraform: failed=0 passed=9
```

Checkov ran 9 IAM-specific rules (CKV_AWS_62, _63, _286-_290, _355, CKV2_AWS_40) and
flagged nothing. Reason: the broadened ARN patterns (`dev/*`, `dev-*`) are still
scoped paths, not literal `*` as resource, and `secretsmanager:GetSecretValue` is a
read-only action. Checkov's default ruleset checks for "no `*` as resource on
restrictable actions" - the policy uses path-prefixed wildcards, not bare `*`, so
the rule passes.

**Implication**: Checkov does NOT catch the specific class of judgment-call concern
PR #8995 represents (path-prefixed wildcard broadening within already-scoped actions).
Its value-add on this PR is zero. It would catch other classes of IaC regression
(public S3, open security groups, missing encryption, literal `*` resource) - those
require separate validation on PRs that exhibit those patterns.

**Decision deferred** (per bead AC): dispatch-trigger vs CI-gate. Soak the feature
on the next 5 IaC PRs before committing to either. If 0 of 5 surface a useful finding,
demote priority and consider closing.
