#!/usr/bin/env bash
# Deploy a CloudFormation stack from infra/<stack>.yaml.
#
# Usage:
#   ./deploy_infra.sh [stack-name]
#
# Defaults: stack-name=marathon-odoo, AWS_PROFILE=nosey, AWS_REGION=us-east-1.
# Optional infra/<stack-name>.params file: one KEY=VALUE per line, # for comments.
set -euo pipefail

STACK_NAME="${1:-marathon-odoo}"
PROFILE="${AWS_PROFILE:-nosey}"
REGION="${AWS_REGION:-us-east-1}"

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${INFRA_DIR}/${STACK_NAME}.yaml"
PARAMS_FILE="${INFRA_DIR}/${STACK_NAME}.params"

if [ ! -f "$TEMPLATE" ]; then
  echo "ERROR: template not found: $TEMPLATE" >&2
  exit 1
fi

PARAM_OVERRIDES=()
if [ -f "$PARAMS_FILE" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="${line## }"; line="${line%% }"
    [ -z "$line" ] && continue
    PARAM_OVERRIDES+=("$line")
  done < "$PARAMS_FILE"
fi

echo "Stack:    $STACK_NAME"
echo "Profile:  $PROFILE"
echo "Region:   $REGION"
echo "Template: $TEMPLATE"
[ -f "$PARAMS_FILE" ] && echo "Params:   $PARAMS_FILE (${#PARAM_OVERRIDES[@]} overrides)"
echo

aws --profile "$PROFILE" --region "$REGION" cloudformation validate-template \
  --template-body "file://${TEMPLATE}" >/dev/null
echo "Template OK."

aws --profile "$PROFILE" --region "$REGION" cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE" \
  --tags "Stack=${STACK_NAME}" \
  --no-fail-on-empty-changeset \
  ${PARAM_OVERRIDES[@]:+--parameter-overrides "${PARAM_OVERRIDES[@]}"}

echo
echo "Outputs:"
aws --profile "$PROFILE" --region "$REGION" cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs' --output table
