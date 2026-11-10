#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/vendor/MoneyPrinterTurbo"
cd "$APP"

exec .venv/bin/python -m streamlit run webui/Main.py \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.port 8501
