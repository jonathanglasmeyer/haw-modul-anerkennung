#!/bin/bash
# Load .env and run command with uv

set -a
source .env
set +a

exec uv run "$@"
