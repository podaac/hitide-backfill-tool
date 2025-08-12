#!/usr/bin/env bash
set -eo pipefail

if [ ! $# -eq 1 ]; then
    echo "Usage: $0 <env>"
    exit 1
fi

ENV="$1"
shift

# Get absolute path to the terraform root
TERRAFORM_ROOT="$(cd "$(dirname "$BASH_SOURCE")/.." && pwd)"

source "$TERRAFORM_ROOT/bin/config.sh" "$ENV"

TFVARS_FILE="$TERRAFORM_ROOT/tfvars/${ENV}.tfvars"

if [ ! -f "$TFVARS_FILE" ]; then
    echo "tfvars file not found: $TFVARS_FILE"
    exit 1
fi

cd "$TERRAFORM_ROOT"
terraform apply -var-file="$TFVARS_FILE"