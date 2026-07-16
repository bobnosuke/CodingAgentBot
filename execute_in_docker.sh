#!/bin/bash

# Usage: execute_in_docker.sh <session_id> <main_file_path>

SESSION_ID=$1
MAIN_FILE_PATH=$2

if [ -z "$SESSION_ID" ] || [ -z "$MAIN_FILE_PATH" ]; then
  echo "Usage: $0 <session_id> <main_file_path>"
  exit 1
fi

PROJECT_DIR="/app/${SESSION_ID}"

# Build the Docker image (if not already built)
docker build -t coderagent-exec:${SESSION_ID} -f Dockerfile.exec .

# Create a temporary directory for the session files
mkdir -p "${PROJECT_DIR}"

# Copy generated files into the temporary directory
# This part will be handled by the Python executor, which will mount the volume

# Run the Docker container
docker run --rm \
  -v "$(pwd)/${SESSION_ID}":/app \
  coderagent-exec:${SESSION_ID} \
  python "${MAIN_FILE_PATH}"

# Clean up temporary directory (handled by Python executor)
# rm -rf "${PROJECT_DIR}"
