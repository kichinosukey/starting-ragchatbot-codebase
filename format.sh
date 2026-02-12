#!/usr/bin/env bash

# format.sh - Black formatter utility for the RAG chatbot project
# Provides three modes: check, format, and diff

set -e

MODE="${1:-check}"

case "$MODE" in
  check)
    echo "🔍 Checking code formatting (dry-run)..."
    uv run black --check backend/ main.py
    echo "✅ All files are properly formatted!"
    ;;

  format)
    echo "🎨 Applying Black formatting..."
    uv run black backend/ main.py
    echo "✅ Formatting complete!"
    ;;

  diff)
    echo "📋 Showing formatting diff..."
    uv run black --diff backend/ main.py
    ;;

  *)
    echo "Usage: ./format.sh {check|format|diff}"
    echo ""
    echo "Modes:"
    echo "  check   - Check if code is formatted (dry-run)"
    echo "  format  - Apply Black formatting to code"
    echo "  diff    - Show detailed diff of formatting changes"
    exit 1
    ;;
esac
