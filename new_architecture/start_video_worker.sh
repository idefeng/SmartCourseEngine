#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "未找到虚拟环境Python: $PYTHON_BIN"
  exit 1
fi

if [ -z "$VIDEO_ANALYZER_URL" ]; then
  export VIDEO_ANALYZER_URL="http://localhost:8002"
fi

exec "$PYTHON_BIN" "$PROJECT_ROOT/video_analysis_worker.py"
