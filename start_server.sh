#!/bin/bash
cd "$(dirname "$0")"
echo "Starting server from $(pwd)" >&2
echo "Server file: $(ls -la server.py)" >&2
/Users/tom/.local/bin/uv run server.py
