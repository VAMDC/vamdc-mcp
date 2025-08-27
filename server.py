# /// script
# requires-python = ">=3.13"
# dependencies = ["fastmcp", "pandas", "pyvamdc @ file:///Users/tom/work/vamdc/carlo-mcp/pyVAMDC"]
# ///

from mcp.server.fastmcp import FastMCP
import pandas as pd
import pyVAMDC.spectral.species as species
import asyncio
import pyVAMDC.spectral.lines as lines
import pyVAMDC.spectral.filters as filters
import sys
import traceback

from typing import List, Optional, Dict, Any

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
            lambdaMin=lambda_min,
            lambdaMax=lambda_max,
            species_dataframe=allSpecies,
            nodes_dataframe=allNodes,
            verbose=False
        )
    
    
    # Get the dictionary of {database_name: dataframe}
    lines_dict = await loop.run_in_executor(None, get_lines_sync)
    
    # Combine all dataframes into a single list of records
    all_records = []
    for database_name, dataframe in lines_dict.items():
        # Convert dataframe to records and add database source info
        records = dataframe.to_dict(orient='records')
        # Add the database name to each record
        for record in records:
            record['source_database'] = database_name
        all_records.extend(records)
    
    return all_records


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





def main():
    """
    Initializes the MCP server, registers the getSpecies tool, and runs the server
    on port 8888 using StreamableHTTPServerTransport with endpoint 'mcp'.
    """
    print("Starting VAMDC MCP Server...")
    
    try:
        # Initialize the server
        print("Initializing FastMCP server...")
        server = FastMCP(
            name="VAMDC MCP Server"
        )
        print("FastMCP server initialized successfully")
        
        @server.tool()
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


        # Register the tools
        @server.tool()
        def get_species() -> list:
            """
            Gets all the chemical information available on the Species Database.
            Returns a list of dictionaries containing chemical species information.
            
            Returns:
                list: A list of dictionaries, each containing:
                    - shortname (str): Human readable name for the database containing the current species
                    - ivoIdentifier (str): Unique identifier for the database containing the current species
                    - InChI (str): InChI chemical unique identifier for the current species
                    - InChIKey (str): InChIKey derived from the InChI for the current species
                    - stoichiometricFormula (str): Stoichiometric formula for the current species
                    - massNumber (int): Mass number for the current species
                    - charge (int): Electric charge for the current species
                    - speciesType (str): Type (admitted values are 'molecule', 'atom', 'particle') for the current species
                    - structuralFormula (str): Structural formula for the current species
                    - name (str): Human readable species name for the current species
                    - did (str): Alternative unique identifier for the current species
                    - tapEndpoint (str): Database TAP-endpoint URL for the database containing the current species
                    - lastIngestionScriptDate (date): Last ingestion script execution for the database containing the current species
                    - speciesLastSeenOn (date): Last time species was updated for the database containing the current species
                    - # unique atoms (int): Number of unique atoms in the current species
                    - # total atoms (int): Total number of atoms in the current species
                    - computed charge (int): Computed charge for the current species
                    - computed mass number (float): Computed mass number for the current species

            """
            return getSpecies()
        
        @server.tool()
        def get_nodes() -> list:
            """
            Gets all the Nodes available on the Species Database.
            Returns a list of dictionaries containing node information.
            
            Returns:
                list: A list of dictionaries, each containing:
                    - shortName (str): Short name identifier for the database node
                    - description (str): Descriptive text about the database node
                    - contactEmail (str): Email address for contacting the node maintainer
                    - ivoIdentifier (str): Unique IVO (International Virtual Observatory) identifier for the node
                    - tapEndpoint (str): TAP (Table Access Protocol) endpoint URL for the database node
                    - referenceUrl (str): Reference URL with additional information about the node
                    - lastUpdate (date): Date when the node was last updated
                    - lastSeen (date): Date when the node was last seen/accessed
                    - topics (list): List of strings describing the scientific topics covered by the node
            """
            return getNodes()

        @server.tool()
        def get_server_info() -> Dict[str, Any]:
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
                "available_tools": ["get_lines", "get_species", "get_nodes"],
                "description": "Server for accessing VAMDC spectroscopic databases",
                "endpoints": {
                "species": "Get all available chemical species",
                "nodes": "Get all available database nodes", 
                "lines": "Get spectral lines within wavelength range"
                }
            }
     

        print("Tools registered, starting MCP stdio server")
        print("Press Ctrl+C to stop the server")
        
        # Run the server using stdio transport
        import asyncio
        asyncio.run(server.run_stdio_async())
    except Exception as e:
        import sys
        sys.stderr.write(f"Error starting server: {e}\n")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


