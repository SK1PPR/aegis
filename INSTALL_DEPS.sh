#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements.txt

echo
echo "Environment ready."
echo "Smoke test: RGOTA_EMBEDDING_BACKEND=hash python tests/quick_test.py"
echo "Paper check: python scripts/verify_paper_results.py /path/to/RGOTA-paper.pdf"
