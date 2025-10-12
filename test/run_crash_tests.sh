#!/bin/bash
# Run all crash and stress tests

echo "=================================================="
echo "JASMIN-LSP CRASH AND STRESS TEST SUITE"
echo "=================================================="
echo ""

# Build first
echo "Building server..."
dune build
if [ $? -ne 0 ]; then
    echo "✗ Build failed!"
    exit 1
fi
echo "✓ Build successful"
echo ""

# Run crash scenarios
echo "Running crash scenario tests..."
python3 test_crash_scenarios.py
CRASH_RESULT=$?
echo ""

# Run stress test
echo "Running stress test..."
python3 test_stress_quick.py
STRESS_RESULT=$?
echo ""

# Summary
echo "=================================================="
echo "TEST SUMMARY"
echo "=================================================="

if [ $CRASH_RESULT -eq 0 ]; then
    echo "✓ Crash scenarios: PASSED"
else
    echo "✗ Crash scenarios: FAILED"
fi

if [ $STRESS_RESULT -eq 0 ]; then
    echo "✓ Stress test: PASSED"
else
    echo "✗ Stress test: FAILED"
fi

echo "=================================================="

if [ $CRASH_RESULT -eq 0 ] && [ $STRESS_RESULT -eq 0 ]; then
    echo "ALL TESTS PASSED! 🎉"
    exit 0
else
    echo "SOME TESTS FAILED"
    exit 1
fi
