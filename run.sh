#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$ROOT/scripts/env.sh"
cd "$ROOT"

exec uv run --active streamlit run src/main.py "$@"
