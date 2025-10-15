# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "mcp",
#     "uvicorn",
#     "pyvamdc @ git+https://github.com/VAMDC/pyVAMDC.git"
# ]
# ///


import argparse
import asyncio
from typing import Any

import httpx
import uvicorn

from mcp.server.fastmcp import FastMCP

import pyVAMDC.spectral.species as species
import pyVAMDC.spectral.filters as filters
import pyVAMDC.spectral.lines as lines

from typing import List, Optional, Dict, Any

mcp = FastMCP(name="vamdc", json_response=True, stateless_http=True)

def getSpecies():
    """
    Gets all the chemical information available on the Species Database. 
    Returns two Pandas dataframe. One for the inforamtion regarding the Nodes, the other for the information regarding the chemical species within the Nodes. 
    """
    species_dataframe , _ = species.getAllSpecies()
    return species_dataframe.to_dict(orient='records')


def getNodes():
    """
    Gets all the Nodes available on the Species Database.
    Returns a Pandas dataframe with information regarding the Nodes.
    """
    _, nodes_dataframe = species.getAllSpecies()
    return nodes_dataframe.to_dict(orient='records')

def format_species_as_markdown_table(species_list: List[Dict[str, Any]]) -> str:
    """
    Formats a list of species dictionaries as a markdown table.

    Args:
        species_list: List of species dictionaries

    Returns:
        Markdown-formatted table string
    """
    # Define columns to include
    columns = [
        'name',
        'stoichiometricFormula',
        'InChIKey',
        'speciesType',
        'charge',
        'massNumber',
        'structuralFormula',
        'shortName',
        '# unique atoms',
        '# total atoms',
        'computed charge',
        'computed mol_weight'
    ]

    # Build markdown table
    header = '| ' + ' | '.join(columns) + ' |'
    separator = '|' + '|'.join(['---' for _ in columns]) + '|'

    table_lines = [header, separator]

    for species_dict in species_list:
        row_values = []
        for col in columns:
            value = species_dict.get(col, '')
            # Convert to string and escape pipe characters
            value_str = str(value).replace('|', '\\|')
            row_values.append(value_str)

        table_lines.append('| ' + ' | '.join(row_values) + ' |')

    return '\n'.join(table_lines)

async def getLines(lambda_min, lambda_max, listNodes=None, listSpecies=None):
    """
    Gets spectral lines data within a specified wavelength range.

    Args:
        lambda_min (float): Lower wavelength bound expressed in Angstrom (mandatory)
        lambda_max (float): Upper wavelength bound expressed in Angstrom (mandatory)
        listNodes (list, optional): List of tap-endpoints (url) node to filter by
        listSpecies (list, optional): List InchiKeys of species to filter by

    Returns:
        list: List of dictionaries containing spectral line information
    """
    # Run the blocking operation in a thread pool
    loop = asyncio.get_event_loop()

    allSpecies , allNodes = species.getAllSpecies()

    if listNodes is not None:
        allNodes = filters.filterDataHavingColumnContainingStrings(
            allNodes,
            'tapEndpoint',
            listNodes
        )

    if listSpecies is not None:
        allSpecies = filters.filterDataHavingColumnContainingStrings(
            allSpecies,
            'InChIKey',
            listSpecies
        )

    def get_lines_sync():
        return lines.getLines(
            lambda_min,
            lambda_max,
            allSpecies,
            allNodes,
            False
        )

    # Get the result (could be dict of dataframes or single dataframe)
    result = await loop.run_in_executor(None, get_lines_sync)

    # Check if result is a dictionary of dataframes (multiple databases)
    if isinstance(result, dict):
        # Combine all dataframes into a single list of records
        all_records = []
        for database_name, dataframe in result.items():
            # Convert dataframe to records and add database source info
            records = dataframe.to_dict(orient='records')
            # Add the database name to each record
            for record in records:
                record['source_database'] = database_name
            all_records.extend(records)
        return all_records
    # Check if result is already a list or needs conversion from DataFrame
    elif hasattr(result, 'to_dict'):
        return result.to_dict(orient='records')
    else:
        return result


@mcp.tool()
async def get_server_info() -> Dict[str, Any]:
    """
    Get information about the VAMDC MCP server and available capabilities.
        
    Returns:
        Dict[str, Any]: Server information including:
            - server_name (str): Name of the server
            - version (str): Server version
            - available_tools (List[str]): List of available tool names
            - description (str): Server description
        """
    return {
                "server_name": "VAMDC MCP Server",
                "version": "1.0.0",
                "available_tools": ["get_server_info", "get_nodes", "get_species", "get_species_by_node", "get_lines"],
                "description": "Server for accessing VAMDC spectroscopic databases",
                "endpoints": {
                "server_info": "Get server information and capabilities",
                "species": "Get all available chemical species",
                "nodes": "Get all available database nodes",
                "species_by_node": "Get chemical species from a specific database node",
                "lines": "Get spectral lines within wavelength range"
            }
    }


@mcp.tool()
async def get_nodes() -> str:
    """
    Gets all the Nodes available on the Species Database.
    Returns a markdown table with all node information.

    Returns:
        str: A markdown-formatted table containing all database nodes with columns:
            - shortName: Short name identifier for the database node
            - tapEndpoint: TAP (Table Access Protocol) endpoint URL for the database node
            - topics: List of scientific topics covered by the node
    """
    nodes = getNodes()

    # Build markdown table
    table_lines = [
        "| Short Name | TAP Endpoint | Topics |",
        "|------------|--------------|--------|"
    ]

    for node in nodes:
        short_name = node.get('shortName', '')
        tap_endpoint = node.get('tapEndpoint', '')
        topics = ', '.join(node.get('topics', []))

        # Escape pipe characters in cell content
        short_name = short_name.replace('|', '\\|')
        tap_endpoint = tap_endpoint.replace('|', '\\|')
        topics = topics.replace('|', '\\|')

        table_lines.append(f"| {short_name} | {tap_endpoint} | {topics} |")

    return "\n".join(table_lines)

@mcp.tool()
async def get_species(state: str) -> str:
    """
    Gets all the chemical information available on the Species Database.
    Returns a markdown table with species information.

    Returns:
        str: A markdown-formatted table containing all chemical species with columns:
            - name: Human readable species name
            - stoichiometricFormula: Stoichiometric formula
            - InChIKey: InChIKey chemical identifier
            - speciesType: Type (molecule, atom, or particle)
            - charge: Electric charge
            - massNumber: Mass number
            - structuralFormula: Structural formula
            - shortName: Database name containing the species
            - # unique atoms: Number of unique atoms
            - # total atoms: Total number of atoms
            - computed charge: Computed charge
            - computed mol_weight: Computed molecular weight
    """
    species_dataframe, _ = species.getAllSpecies()
    species_list = species_dataframe.to_dict(orient='records')
    return format_species_as_markdown_table(species_list)


@mcp.tool()
async def get_species_by_node(node_url: str) -> str:
    """
    Gets chemical species data from a specific VAMDC database node.
    Returns a markdown table with species information.

    Args:
        node_url (str): The TAP endpoint URL of the database node to query.
                       Example: "http://vald.astro.uu.se/atoms-12.07/tap/"

    Returns:
        str: A markdown-formatted table containing species information from the specified node,
        with the same columns as get_species but filtered to the specific database node.
    """
    # Run the blocking operation in a thread pool
    loop = asyncio.get_event_loop()

    def get_species_by_node_sync():
        # Query the specific node by filtering all species for this node's TAP endpoint
        all_species_df, _ = species.getAllSpecies()

        # Filter species to only those from the specified node
        node_species_df = all_species_df[all_species_df['tapEndpoint'] == node_url]

        return node_species_df.to_dict(orient='records')

    species_list = await loop.run_in_executor(None, get_species_by_node_sync)
    return format_species_as_markdown_table(species_list)


@mcp.tool()
async def get_lines(
            lambda_min: float,
            lambda_max: float,
            listNodes: Optional[List[str]] = None,
            listSpecies: Optional[List[str]] = None
        ) -> List[Dict[str, Any]]:
    """
            Gets spectral lines data within a specified wavelength range.

            Args:
                lambda_min (float): Lower wavelength bound in Angstrom (mandatory)
                lambda_max (float): Upper wavelength bound in Angstrom (mandatory)
                listNodes (List[str], optional): List of database tap-endpoints (URLs) to filter the search by specific databases. This list may be optained by quering the get_nodes tool on this server.
                            Example: ["http://cdms.astro.uni-koeln.de/tap", "http://jpl.nasa.gov/tap"]
                listSpecies (List[str], optional): List of InChIKeys of species to filter the search by. This list may be obtained by querying the get_species tool on this server.
                            Example: ["UGFAIRIUMAVXCW-UHFFFAOYSA-N", "XLYOFNOQVPJJNP-UHFFFAOYSA-N"]


            Returns:
              List[Dict[str, Any]]: A list of dictionaries containing spectral line information, each containing:
                    - InChIKey (str): InChI Key chemical unique identifier for the species
                    - InChI (str): InChI chemical unique identifier for the species
                    - Chemical name (str): Human readable name of the chemical species
                    - Stoichiometric formula (str): Stoichiometric formula of the species
                    - Ordinary structural formula (str): Structural formula of the species
                    - Frequency (float): Frequency of the spectral line
                    - A (float): Einstein A coefficient for the transition
                    - Lower energy(1/cm) (float): Lower state energy in wavenumbers (cm⁻¹)
                    - Lower total statistical weight (int): Total statistical weight of the lower state
                    - Lower nuclear statistical weight (int): Nuclear statistical weight of the lower state
                    - Lower QNs (str): Quantum numbers of the lower state
                    - Upper energy(1/cm) (float): Upper state energy in wavenumbers (cm⁻¹)
                    - Upper total statistical weight (int): Total statistical weight of the upper state
                    - Upper nuclear statistical weight (int): Nuclear statistical weight of the upper state
                    - Upper QNs (str): Quantum numbers of the upper state
                    - queryToken (str): Token identifying the query that produced this line
                    - source_database (str): Name of the database that provided this line data

            Example:
                await get_lines(4000.0, 5000.0, listSpecies=["UGFAIRIUMAVXCW-UHFFFAOYSA-N"])
            """
    return await getLines(lambda_min, lambda_max, listNodes, listSpecies)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run VAMDC MCP server")
    parser.add_argument(
        "--transport",
        type=str,
        choices=["http", "stdio"],
        default="http",
        help="Transport protocol to use: 'http' for Streamable HTTP (web/remote access) or 'stdio' for standard input/output (desktop apps)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to listen on (only used with --transport http)"
    )
    args = parser.parse_args()

    if args.transport == "http":
        # Start the server with Streamable HTTP transport
        print(f"Starting VAMDC MCP server with HTTP transport on http://localhost:{args.port}/mcp")
        uvicorn.run(mcp.streamable_http_app, host="localhost", port=args.port)
    else:
        # Start the server with stdio transport (log to stderr to avoid interfering with JSON-RPC)
        import sys
        print("Starting VAMDC MCP server with stdio transport", file=sys.stderr, flush=True)
        asyncio.run(mcp.run_stdio_async())
