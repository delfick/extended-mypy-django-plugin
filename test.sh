#!/bin/bash

set -e

cd "$(git rev-parse --show-toplevel)"

# The virtualenv needs to be active for it to find mypy
source ./dev activate

exec ./dev tests "$@"
