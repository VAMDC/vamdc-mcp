#!/usr/bin/env python3
#
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
# ]
# ///

"""
Simple synchronous client to test the getSpecies tool from the VAMDC MCP server.
"""

import json
import requests
import argparse


def call_mcp_tool_sse(server_url: str, tool_name: str, arguments: dict = None):
    """
    Call a tool on the MCP server using Server-Sent Events (SSE).
    """
    if arguments is None:
        arguments = {}
    
    # Prepare the MCP request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    try:
        # Try SSE approach
        response = requests.post(
            f"{server_url}/message",
            json=mcp_request,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            timeout=30,
            stream=True
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        # Fallback to direct root endpoint
        try:
            response = requests.post(
                server_url,
                json=mcp_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e2:
            print(f"Both SSE and direct requests failed:")
            print(f"SSE error: {e}")
            print(f"Direct error: {e2}")
            raise


def call_mcp_tool(server_url: str, tool_name: str, arguments: dict = None):
    """
    Call a tool on the MCP server using synchronous requests.
    
    Args:
        server_url: Base URL of the MCP server
        tool_name: Name of the tool to call
        arguments: Arguments to pass to the tool
    
    Returns:
        Response from the server
    """
    if arguments is None:
        arguments = {}
    
    # Prepare the MCP request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    # Try different endpoints that FastMCP might use
    endpoints_to_try = [
        "",  # Root endpoint
        "/message",  # Message endpoint for streamable HTTP
        "/sse",  # SSE endpoint
        "/mcp",  # MCP endpoint
    ]
    
    for endpoint in endpoints_to_try:
        try:
            url = f"{server_url}{endpoint}" if endpoint else server_url
            print(f"   Trying endpoint: {url}")
            
            # Send POST request to the server
            response = requests.post(
                url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=30
            )
            
            # Check if the HTTP request was successful
            response.raise_for_status()
            
            # Parse and return the JSON response
            result = response.json()
            print(f"   ✓ Success with endpoint: {url}")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"   ✗ Failed with endpoint {url}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"     Response: {e.response.text}")
            continue
        except json.JSONDecodeError as e:
            print(f"   ✗ JSON decode error for {url}: {e}")
            print(f"     Response text: {response.text}")
            continue
    
    raise Exception("All endpoint attempts failed")


def list_tools(server_url: str):
    """List all available tools on the server."""
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    # Try different endpoints that FastMCP might use
    endpoints_to_try = [
        "",  # Root endpoint
        "/message",  # Message endpoint for streamable HTTP
        "/sse",  # SSE endpoint
        "/mcp",  # MCP endpoint
    ]
    
    for endpoint in endpoints_to_try:
        try:
            url = f"{server_url}{endpoint}" if endpoint else server_url
            print(f"   Trying tools/list at: {url}")
            
            response = requests.post(
                url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            print(f"   ✓ Success listing tools at: {url}")
            return result
        except Exception as e:
            print(f"   ✗ Failed listing tools at {url}: {e}")
            continue
    
    raise Exception("Could not list tools from any endpoint")


def test_all_tools(server_url: str):
    """Test all available tools on the VAMDC MCP server."""
    print(f"Testing VAMDC MCP server at {server_url}")
    print("=" * 60)
    
    try:
        # Test server connectivity
        print("1. Testing server connectivity...")
        try:
            response = requests.get(f"{server_url}/health", timeout=5)
            print(f"   Health check status: {response.status_code}")
        except:
            print("   Health endpoint not available, proceeding with tool tests...")
        
        # List available tools
        print("\n2. Listing available tools...")
        tools_response = list_tools(server_url)
        print(f"   Tools response: {json.dumps(tools_response, indent=4)}")
        
        # Test get_server_info tool
        print("\n3. Testing get_server_info tool...")
        try:
            server_info_response = call_mcp_tool(server_url, "get_server_info")
            print("   ✓ Server info response received successfully!")
            
            if isinstance(server_info_response, dict) and "result" in server_info_response:
                result_data = server_info_response["result"]
                print(f"\n   Server Information:")
                for key, value in result_data.items():
                    print(f"   • {key}: {value}")
            else:
                print(f"   Full response: {json.dumps(server_info_response, indent=4)}")
                
        except Exception as e:
            print(f"   ❌ get_server_info failed: {e}")
        
        # Test get_nodes tool
        print("\n4. Testing get_nodes tool...")
        try:
            nodes_response = call_mcp_tool(server_url, "get_nodes")
            print("   ✓ Nodes response received successfully!")
            
            if isinstance(nodes_response, dict) and "result" in nodes_response:
                result_data = nodes_response["result"]
                if isinstance(result_data, list):
                    print(f"\n   Nodes data analysis:")
                    print(f"   • Total nodes found: {len(result_data)}")
                    
                    if len(result_data) > 0:
                        print(f"\n   • Sample nodes (first 2):")
                        for i, node in enumerate(result_data[:2]):
                            if isinstance(node, dict):
                                print(f"     Node {i+1}:")
                                for key, value in list(node.items())[:5]:  # Show first 5 fields
                                    print(f"       {key}: {value}")
                                print("       ...")
                            else:
                                print(f"     {i+1}. {node}")
                        
                        if len(result_data) > 2:
                            print(f"   • ... and {len(result_data) - 2} more nodes")
                else:
                    print(f"\n   Result data: {result_data}")
            else:
                print(f"   Full response: {json.dumps(nodes_response, indent=4)}")
                
        except Exception as e:
            print(f"   ❌ get_nodes failed: {e}")
        
        # Test the get_species tool
        print("\n5. Testing get_species tool...")
        try:
            species_response = call_mcp_tool(server_url, "get_species", {"state": "test"})
            print("   ✓ Species response received successfully!")
            
            # Process and display the response
            if isinstance(species_response, dict) and "result" in species_response:
                result_data = species_response["result"]
                
                if isinstance(result_data, list):
                    print(f"\n   Species data analysis:")
                    print(f"   • Total species found: {len(result_data)}")
                    
                    if len(result_data) > 0:
                        print(f"\n   • Sample species (first 3):")
                        for i, species in enumerate(result_data[:3]):
                            if isinstance(species, dict):
                                # Show only key fields to avoid overwhelming output
                                key_fields = ['name', 'stoichiometricFormula', 'shortName', 'massNumber']
                                print(f"     Species {i+1}:")
                                for field in key_fields:
                                    if field in species:
                                        print(f"       {field}: {species[field]}")
                            else:
                                print(f"     {i+1}. {species}")
                        
                        # Show column information if it's a dict-like structure
                        if isinstance(result_data[0], dict):
                            columns = list(result_data[0].keys())
                            print(f"\n   • Available columns ({len(columns)}): {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}")
                        
                        if len(result_data) > 3:
                            print(f"   • ... and {len(result_data) - 3} more species")
                            
                else:
                    print(f"\n   Result data: {result_data}")
            else:
                print(f"   Full response: {json.dumps(species_response, indent=4)}")
                
        except Exception as e:
            print(f"   ❌ get_species failed: {e}")
        
        # Test the get_lines tool
        print("\n6. Testing get_lines tool...")
        try:
            # Test with specific parameters as requested
            lines_response = call_mcp_tool(server_url, "get_lines", {
                "lambda_min": 1000.0,
                "lambda_max": 1008.0,
                "listNodes": ["http://topbase.obspm.fr/12.07/vamdc/tap/"],
                "listSpecies": ["CWYNVVGOOAEACU-UHFFFAOYSA-N"]
            })
            print("   ✓ Lines response received successfully!")
            
            # Process and display the response
            if isinstance(lines_response, dict) and "result" in lines_response:
                result_data = lines_response["result"]
                
                if isinstance(result_data, list):
                    print(f"\n   Spectral lines data analysis:")
                    print(f"   • Total spectral lines found: {len(result_data)}")
                    print(f"   • Wavelength range: 1000-1008 Angstrom")
                    print(f"   • Node: http://topbase.obspm.fr/12.07/vamdc/tap/")
                    print(f"   • Species: CWYNVVGOOAEACU-UHFFFAOYSA-N")
                    
                    if len(result_data) > 0:
                        print(f"\n   • Sample spectral lines (first 2):")
                        for i, line in enumerate(result_data[:2]):
                            if isinstance(line, dict):
                                # Show key spectroscopic fields
                                key_fields = ['Chemical name', 'Stoichiometric formula', 'Frequency', 'A', 'Lower energy(1/cm)', 'Upper energy(1/cm)']
                                print(f"     Line {i+1}:")
                                for field in key_fields:
                                    if field in line:
                                        print(f"       {field}: {line[field]}")
                                print("       ...")
                            else:
                                print(f"     {i+1}. {line}")
                        
                        # Show column information if it's a dict-like structure
                        if isinstance(result_data[0], dict):
                            columns = list(result_data[0].keys())
                            print(f"\n   • Available columns ({len(columns)}): {', '.join(columns[:8])}{'...' if len(columns) > 8 else ''}")
                        
                        if len(result_data) > 2:
                            print(f"   • ... and {len(result_data) - 2} more spectral lines")
                    else:
                        print("\n   • No spectral lines found in the specified range and filters")
                            
                else:
                    print(f"\n   Result data: {result_data}")
            else:
                print(f"   Full response: {json.dumps(lines_response, indent=4)}")
                
        except Exception as e:
            print(f"   ❌ get_lines failed: {e}")
        
        print(f"\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Simple test client for VAMDC MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python simple_client.py                    # Test server on default port 8888
  python simple_client.py --port 9999       # Test server on port 9999
  python simple_client.py --url http://example.com:8888  # Test remote server
        """
    )
    parser.add_argument("--url", default="http://localhost:8888", 
                       help="Server URL (default: http://localhost:8888)")
    parser.add_argument("--port", type=int, 
                       help="Server port (overrides URL)")
    
    args = parser.parse_args()
    
    # If port is specified, construct URL with that port
    server_url = args.url
    if args.port:
        server_url = f"http://localhost:{args.port}"
    
    test_all_tools(server_url)


if __name__ == "__main__":
    main()
