#!/bin/bash

# This script runs all pytest tests in the tests/ directory, ensuring the correct PYTHONPATH.

# Get the directory of this script to reliably find the project root.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Change to the project root directory.
cd "$PROJECT_ROOT"

# Activate the virtual environment.
source back/venv/bin/activate

# Add the project root to the PYTHONPATH to resolve 'from back.app...' imports.
export PYTHONPATH="$PWD"

TEST_ARGS="$@"
if [ -z "$TEST_ARGS" ]; then
    TEST_ARGS="back/tests/"
fi

# Check if running integration tests to enable DEBUG logs
if [[ "$TEST_ARGS" == *"integration"* ]]; then
    echo "Integration tests detected: Enabling DEBUG logs for detailed LLM tracking."
    # Enable CLI logging at DEBUG level
    PYTEST_OPTS="-o log_cli=true -o log_cli_level=DEBUG"
else
    PYTEST_OPTS=""
fi

echo "Running tests: $TEST_ARGS"
echo "------------------------"

# Run tests
pytest $TEST_ARGS $PYTEST_OPTS

