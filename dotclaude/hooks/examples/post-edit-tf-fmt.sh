#!/usr/bin/env bash
# PostToolUse hook: auto-format Terraform/HCL files after Edit/Write
# Runs terraform fmt on the changed file. Silent on success.
set -euo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only process .tf and .hcl files
if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi
case "$FILE_PATH" in
  *.tf|*.tfvars|*.hcl) ;;
  *) exit 0 ;;
esac

# Only process files under the project
if [[ "$FILE_PATH" != /workspaces/main/* ]]; then
  exit 0
fi

# terraform fmt formats the file in-place; handles .tf, .tfvars, and .hcl
terraform fmt "$FILE_PATH" 2>/dev/null || true

exit 0
