# VAMDC MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for accessing VAMDC (Virtual Atomic and Molecular Data Centre) spectroscopic databases.

## Overview

MCP server providing access to VAMDC spectroscopic databases through the Model Context Protocol. Built on [pyVAMDC](https://github.com/VAMDC/pyVAMDC) for querying atomic and molecular data from distributed databases worldwide.

## Features

- **5 MCP Tools** for querying spectroscopic data:
  - `get_server_info` - Server capabilities and metadata
  - `get_nodes` - List all available VAMDC database nodes (33 databases)
  - `get_species` - Get chemical species data (4,952+ species)
  - `get_species_by_node` - Filter species by specific database node
  - `get_lines` - Query spectral lines within wavelength range

- **Dual Transport Support**:
  - **HTTP** (Streamable HTTP) - For web/remote access
  - **stdio** - For desktop MCP clients (Claude Desktop, IDEs)

- **Clean Architecture**: Module-level tool registration, async execution with thread pools

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

Clone the repository:

```bash
git clone https://github.com/VAMDC/vamdc-mcp.git
cd vamdc-mcp
```

No additional installation needed - `uv` will handle dependencies automatically.

## Usage

### Starting the Server

#### HTTP Transport (Default)

Start the server with HTTP transport for web/remote access:

```bash
uv run server.py --transport http --port 8888
```

The server will be available at `http://localhost:8888/mcp`

**Change port** (optional):
```bash
uv run server.py --transport http --port 9000
```

#### stdio Transport

Start the server with stdio transport for desktop MCP clients:

```bash
uv run server.py --transport stdio
```

This mode is used by desktop applications like Claude Desktop, VSCode extensions, etc.

### Command Line Options

```bash
uv run server.py --help
```

**Options**:
- `--transport {http,stdio}` - Transport protocol (default: `http`)
- `--port PORT` - Port for HTTP transport (default: `8888`)

## Examples

### HTTP Transport Example

Using `curl` to interact with the HTTP server:

```bash
# 1. Initialize the session
curl -X POST "http://localhost:8888/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "protocolVersion":"2025-03-26",
      "capabilities":{},
      "clientInfo":{"name":"test-client","version":"1.0.0"}
    }
  }'

# 2. List available tools
curl -X POST "http://localhost:8888/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# 3. Get database nodes
curl -X POST "http://localhost:8888/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{"name":"get_nodes","arguments":{}}
  }'

# 4. Get species from specific node (AMDIS Ionization)
curl -X POST "http://localhost:8888/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0",
    "id":4,
    "method":"tools/call",
    "params":{
      "name":"get_species_by_node",
      "arguments":{"node_url":"http://dbshino.nifs.ac.jp:4000/vamdc/tap/"}
    }
  }'

# 5. Query spectral lines (1000-1500 Angstrom, Magnesium from VALD)
curl -X POST "http://localhost:8888/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0",
    "id":5,
    "method":"tools/call",
    "params":{
      "name":"get_lines",
      "arguments":{
        "lambda_min":1000.0,
        "lambda_max":1500.0,
        "listNodes":["http://vald.astro.uu.se/atoms-12.07/tap/"],
        "listSpecies":["FYYHWMGAXLPEAU-UHFFFAOYSA-N"]
      }
    }
  }'
```

### stdio Transport Example

Using echo/pipe for stdio communication:

```bash
# Send initialize request
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | uv run server.py --transport stdio

# Interactive session with multiple requests
cat <<'EOF' | uv run server.py --transport stdio
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_server_info","arguments":{}}}
EOF
```

### Claude Desktop Configuration

To use with Claude Desktop, add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Option 1: Using the start script (recommended)

```json
{
  "mcpServers": {
    "vamdc": {
      "command": "bash",
      "args": ["/path/to/vamdc-mcp/start_server.sh"]
    }
  }
}
```

#### Option 2: Direct uv command

```json
{
  "mcpServers": {
    "vamdc": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/vamdc-mcp",
        "server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

Replace `/path/to/vamdc-mcp` with the actual path to your cloned repository.

**Note**: The `start_server.sh` script is included for convenience and handles directory navigation automatically.

## Available Tools

### 1. get_server_info
Get server metadata and capabilities.

**Parameters**: None

**Returns**: Server name, version, available tools list

### 2. get_nodes
List all VAMDC database nodes.

**Parameters**: None

**Returns**: 33 database nodes with metadata (name, TAP endpoint, topics, contact info)

### 3. get_species
Get all chemical species data.

**Parameters**:
- `state` (string): State filter (currently not implemented, accepts any value)

**Returns**: 4,952+ species with InChI, InChIKey, formulas, charges, masses

### 4. get_species_by_node
Filter species by specific database node.

**Parameters**:
- `node_url` (string): TAP endpoint URL of the database node
  - Example: `"http://vald.astro.uu.se/atoms-12.07/tap/"`

**Returns**: Filtered species list from specified node

### 5. get_lines
Query spectral lines within wavelength range.

**Parameters**:
- `lambda_min` (float): Lower wavelength bound in Angstrom (required)
- `lambda_max` (float): Upper wavelength bound in Angstrom (required)
- `listNodes` (array of strings, optional): Filter by TAP endpoint URLs
- `listSpecies` (array of strings, optional): Filter by InChIKeys

**Returns**: Spectral line data including frequencies, Einstein coefficients, energy levels, quantum numbers

**Note**: This tool queries remote VAMDC databases, which may be slow or timeout depending on the wavelength range and filters.

## Architecture

- **FastMCP Framework**: Built on the official MCP Python implementation
- **Async Execution**: Thread pool execution for blocking database operations
- **Stateless HTTP**: No session state maintained between requests
- **Module-level Tools**: Clean, flat structure for easy maintenance

## Dependencies

Managed automatically by `uv`:
- `mcp` - Model Context Protocol implementation
- `uvicorn` - ASGI server for HTTP transport
- `pyVAMDC` - Python interface to VAMDC databases ([GitHub](https://github.com/VAMDC/pyVAMDC))
  - Handles queries to remote VAMDC TAP endpoints
  - Processes spectroscopic data from multiple databases
  - Provides filtering and data manipulation utilities

## Testing

See `mcp_server_test_log.md` for comprehensive testing documentation.

## Protocol Version

Implements MCP protocol version **2025-03-26**

## License

See repository for license information.

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.

## Links

- [VAMDC Portal](https://portal.vamdc.eu/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [GitHub Repository](https://github.com/VAMDC/vamdc-mcp)
