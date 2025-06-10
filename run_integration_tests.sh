#!/bin/bash

# Integration test runner for dub_video project
# This script runs the integration tests in the correct order

echo "🎬 Running dub_video integration tests..."
echo "⚠️  Note: These tests require:"
echo "   - RUN_NETWORK_TESTS=1 environment variable"
echo "   - OPENAI_API_KEY environment variable (for dubber tests)"
echo ""

# Check if required environment variables are set
if [ -z "$RUN_NETWORK_TESTS" ]; then
    echo "❌ RUN_NETWORK_TESTS is not set. Set it to '1' to run integration tests."
    echo "   Example: RUN_NETWORK_TESTS=1 OPENAI_API_KEY=your-key ./run_integration_tests.sh"
    exit 1
fi

# Run video_preparer tests first (to prepare the data)
echo "1️⃣  Running video_preparer tests..."
pytest tests/test_video_preparer.py -v

# Check if video_preparer tests passed
if [ $? -ne 0 ]; then
    echo "❌ video_preparer tests failed. Cannot proceed with dubber tests."
    exit 1
fi

# Run dubber tests (uses data prepared by video_preparer)
echo ""
echo "2️⃣  Running dubber tests..."
pytest tests/test_dubber.py -v

echo ""
echo "✅ Integration tests completed!" 