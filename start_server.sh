#!/bin/bash
# Start VAMDC MCP server for Claude Desktop (stdio mode)
# This script finds uv in common installation locations

cd "$(dirname "$0")"

# Try to find uv in common locations
if command -v uv &> /dev/null; then
    UV_CMD="uv"
elif [ -f "$HOME/.local/bin/uv" ]; then
    UV_CMD="$HOME/.local/bin/uv"
elif [ -f "$HOME/.cargo/bin/uv" ]; then
    UV_CMD="$HOME/.cargo/bin/uv"
elif [ -f "/usr/local/bin/uv" ]; then
    UV_CMD="/usr/local/bin/uv"
else
    echo "Error: uv not found. Please install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

exec "$UV_CMD" run server.py --transport stdio
