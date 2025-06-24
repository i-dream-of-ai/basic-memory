#!/bin/bash
set -e

# Initialize Basic Memory configuration for Docker
CONFIG_DIR="/root/.basic-memory"
CONFIG_FILE="$CONFIG_DIR/config.json"
DATA_DIR="/app/data"

echo "Initializing Basic Memory Docker configuration..."

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Create config.json if it doesn't exist or if it doesn't point to the correct data directory
if [ ! -f "$CONFIG_FILE" ] || ! grep -q '"main".*"/app/data"' "$CONFIG_FILE" 2>/dev/null; then
    echo "Creating config.json pointing to mounted volume at $DATA_DIR"
    cat > "$CONFIG_FILE" << EOF
{
  "projects": {
    "main": "$DATA_DIR"
  },
  "default_project": "main",
  "env": "user",
  "log_level": "INFO",
  "sync_changes": true,
  "sync_delay": 1000,
  "update_permalinks_on_move": false
}
EOF
else
    echo "Config file already exists and points to correct data directory"
fi

# Ensure data directory exists
mkdir -p "$DATA_DIR"

echo "Configuration initialized successfully"
echo "Config file contents:"
cat "$CONFIG_FILE"

# Execute the original command
exec "$@"