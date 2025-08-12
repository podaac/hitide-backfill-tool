#!/usr/bin/env bash
set -eo pipefail

if [ ! $# -eq 1 ]; then
    echo "Usage: $0 <env>"
    exit 1
fi

ENV="$1"
shift

source "$(dirname $BASH_SOURCE)/config.sh" "$ENV"

TFVARS_FILE="../tfvars/${ENV}.tfvars"

if [ ! -f "$TFVARS_FILE" ]; then
    echo "tfvars file not found: $TFVARS_FILE"
    exit 1
fi

terraform apply -var-file="$TFVARS_FILE"