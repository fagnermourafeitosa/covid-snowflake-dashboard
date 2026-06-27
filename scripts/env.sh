#!/usr/bin/env bash
# Wire uv to the pyenv virtualenv defined in .python-version.
set -euo pipefail

if ! command -v pyenv >/dev/null 2>&1; then
  echo "pyenv is required but not installed." >&2
  exit 1
fi

eval "$(pyenv init -)"

export VIRTUAL_ENV="$(pyenv prefix)"
export UV_PROJECT_ENVIRONMENT="$VIRTUAL_ENV"
export UV_PYTHON="$VIRTUAL_ENV/bin/python"
