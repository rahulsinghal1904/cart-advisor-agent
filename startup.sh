#!/bin/bash

# Debug information
echo "Current directory: $(pwd)"
echo "Listing directory contents:"
ls -la

# Import environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading .env file"
    set -a
    source .env
    set +a
fi

# Ensure PYTHONPATH is set
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Print Python version and PORT info
echo "Python version: $(python3 --version)"
echo "PORT environment variable: $PORT"

# Start the application
echo "Starting ECommerceAgent application..."
python3 -m e_commerce_agent.src.e_commerce_agent.e_commerce_agent
