#!/bin/bash

# Create preview directory with correct permissions if it doesn't exist
mkdir -p /app/preview

# Change ownership of the preview directory to match the user running the container
chown -R $(id -u):$(id -g) /app/preview

# Make sure the directory is writable
chmod -R 755 /app/preview

# Execute the main command
exec "$@"