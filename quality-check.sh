#!/usr/bin/env bash

# quality-check.sh - Comprehensive quality gate for the RAG chatbot project
# Runs formatting checks and tests

set -e

echo "🚀 Running Quality Checks..."
echo ""

echo "📋 Step 1/2: Checking code formatting..."
if ! uv run black --check backend/ main.py; then
    echo "❌ Code formatting check failed!"
    echo "💡 Run './format.sh format' to fix formatting issues"
    exit 1
fi
echo "✅ Code formatting passed!"
echo ""

echo "🧪 Step 2/2: Running test suite..."
uv run pytest
echo "✅ Tests passed!"
echo ""

echo "🎉 All quality checks passed!"
