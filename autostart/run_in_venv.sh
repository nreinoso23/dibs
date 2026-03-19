#!/bin/bash
# Wrapper to run Python scripts in venv

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    echo "Using venv: $VENV_DIR"
else
    echo "No venv found at $VENV_DIR, using system Python"
fi

# Run the command passed as arguments
"$@"
