#!/usr/bin/env bash

set -euo pipefail

script_dir=$(dirname "${BASH_SOURCE[0]}")

echo Checking Python code with mypy...
mypy "$script_dir/inventory-collector.py" --config-file "$script_dir/mypy.ini"

"$script_dir/inventory-collector.py" "$@"
