#!/bin/bash

# Debug information
echo "Current directory: $(pwd)"
echo "Listing directory contents:"
ls -la
echo "Listing application directory:"
ls -la e_commerce_agent/
echo "PORT environment variable: $PORT"

# Import env variables from .env if it exists
if [ -f .env ]; then
    echo "Loading .env file"
    set -a
    source .env
    set +a
fi

# Ensure PYTHONPATH is set
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Print Python path for debugging
echo "PYTHONPATH: $PYTHONPATH"
echo "Python version: $(python --version)"

# Check if the app.py file exists
if [ -f e_commerce_agent/src/e_commerce_agent/app.py ]; then
    echo "Found app.py, starting application using new entry point"
    # Explicitly start the app on the provided PORT
    echo "Starting application on port $PORT"
    python e_commerce_agent/src/e_commerce_agent/app.py
else
    echo "app.py not found, falling back to e_commerce_agent.py"
    # Explicitly start the app on the provided PORT
    echo "Starting application on port $PORT"
    cd e_commerce_agent/
    python src/e_commerce_agent/e_commerce_agent.py 