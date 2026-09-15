#!/usr/bin/env sh

# Run the complete Python quality gate inside the Docker development image.
# This script checks formatting and types; it does not change source files.
set -eu

# Allow the script to be called from any working directory.
cd "$(dirname "$0")/.."

docker compose run --rm --no-deps test sh -c '
  ruff check . &&
  black --check app tests &&
  isort --check app tests &&
  mypy app
'
