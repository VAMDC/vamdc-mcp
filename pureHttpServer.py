import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

import pandas as pd
import pyVAMDC.spectral.species as species
import pyVAMDC.spectral.lines as lines
import pyVAMDC.spectral.filters as filters

from typing import List, Optional, Dict, Any

def getLines(lambda_min, lambda_max, listNodes=None, listSpecies=None):
    allSpecies, allNodes = species.getAllSpecies()
    if listNodes is not None:
        allNodes = filters.filterDataHavingColumnContainingStrings(
            allNodes, 'tapEndpoint', listNodes
        )
    if listSpecies is not None:
        allSpecies = filters.filterDataHavingColumnContainingStrings(
            allSpecies, 'InChIKey', listSpecies
        )
    lines_dict = lines.getLines(
        lambda_min=lambda_min,
        lambda_max=lambda_max,
        species_dataframe=allSpecies,
        nodes_dataframe=allNodes,
        verbose=False
    )
    all_records = []
    for database_name, dataframe in lines_dict.items():
        records = dataframe.to_dict(orient='records')
        for record in records:
            record['source_database'] = database_name
        all_records.extend(records)
    return all_records

def getSpecies():
    species_dataframe, _ = species.getAllSpecies()
    return species_dataframe.to_dict(orient='records')

def getNodes():
    _, nodes_dataframe = species.getAllSpecies()
    return nodes_dataframe.to_dict(orient='records')

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "VAMDC MCP HTTP Server",
        "version": "1.0.0",
        "description": "Pure HTTP server for VAMDC MCP, exposing spectral lines, species, and nodes."
    },
    "paths": {
        "/lines": {
            "get": {
                "summary": "Get spectral lines within a wavelength range",
                "description": (
                    "Gets spectral lines data within a specified wavelength range.\n\n"
                    "Returns a list of dictionaries containing spectral line information, each containing:\n"
                    "- InChIKey (str): InChI Key chemical unique identifier for the species\n"
                    "- InChI (str): InChI chemical unique identifier for the species\n"
                    "- Chemical name (str): Human readable name of the chemical species\n"
                    "- Stoichiometric formula (str): Stoichiometric formula of the species\n"
                    "- Ordinary structural formula (str): Structural formula of the species\n"
                    "- Frequency (float): Frequency of the spectral line\n"
                    "- A (float): Einstein A coefficient for the transition\n"
                    "- Lower energy(1/cm) (float): Lower state energy in wavenumbers (cm⁻¹)\n"
                    "- Lower total statistical weight (int): Total statistical weight of the lower state\n"
                    "- Lower nuclear statistical weight (int): Nuclear statistical weight of the lower state\n"
                    "- Lower QNs (str): Quantum numbers of the lower state\n"
                    "- Upper energy(1/cm) (float): Upper state energy in wavenumbers (cm⁻¹)\n"
                    "- Upper total statistical weight (int): Total statistical weight of the upper state\n"
                    "- Upper nuclear statistical weight (int): Nuclear statistical weight of the upper state\n"
                    "- Upper QNs (str): Quantum numbers of the upper state\n"
                    "- queryToken (str): Token identifying the query that produced this line\n"
                    "- source_database (str): Name of the database that provided this line data"
                ),
                "parameters": [
                    {
                        "name": "lambda_min",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "number"},
                        "description": "Lower wavelength bound in Angstrom (mandatory)"
                    },
                    {
                        "name": "lambda_max",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "number"},
                        "description": "Upper wavelength bound in Angstrom (mandatory)"
                    },
                    {
                        "name": "listNodes",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "array", "items": {"type": "string"}},
                        "description": "List of database tap-endpoints (URLs) to filter the search by specific databases."
                    },
                    {
                        "name": "listSpecies",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "array", "items": {"type": "string"}},
                        "description": "List of InChIKeys of species to filter the search by."
                    }
                ],
                "responses": {
                    "200": {
                        "description": "A list of dictionaries containing spectral line information.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "InChIKey": {"type": "string", "description": "InChI Key chemical unique identifier for the species"},
                                            "InChI": {"type": "string", "description": "InChI chemical unique identifier for the species"},
                                            "Chemical name": {"type": "string", "description": "Human readable name of the chemical species"},
                                            "Stoichiometric formula": {"type": "string", "description": "Stoichiometric formula of the species"},
                                            "Ordinary structural formula": {"type": "string", "description": "Structural formula of the species"},
                                            "Frequency": {"type": "number", "description": "Frequency of the spectral line"},
                                            "A": {"type": "number", "description": "Einstein A coefficient for the transition"},
                                            "Lower energy(1/cm)": {"type": "number", "description": "Lower state energy in wavenumbers (cm⁻¹)"},
                                            "Lower total statistical weight": {"type": "integer", "description": "Total statistical weight of the lower state"},
                                            "Lower nuclear statistical weight": {"type": "integer", "description": "Nuclear statistical weight of the lower state"},
                                            "Lower QNs": {"type": "string", "description": "Quantum numbers of the lower state"},
                                            "Upper energy(1/cm)": {"type": "number", "description": "Upper state energy in wavenumbers (cm⁻¹)"},
                                            "Upper total statistical weight": {"type": "integer", "description": "Total statistical weight of the upper state"},
                                            "Upper nuclear statistical weight": {"type": "integer", "description": "Nuclear statistical weight of the upper state"},
                                            "Upper QNs": {"type": "string", "description": "Quantum numbers of the upper state"},
                                            "queryToken": {"type": "string", "description": "Token identifying the query that produced this line"},
                                            "source_database": {"type": "string", "description": "Name of the database that provided this line data"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/species": {
            "get": {
                "summary": "Get all chemical species",
                "description": (
                    "Gets all the chemical information available on the Species Database.\n"
                    "Returns a list of dictionaries, each containing chemical species information."
                ),
                "responses": {
                    "200": {
                        "description": "A list of dictionaries, each containing chemical species information.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "shortname": {"type": "string", "description": "Human readable name for the database containing the current species"},
                                            "ivoIdentifier": {"type": "string", "description": "Unique identifier for the database containing the current species"},
                                            "InChI": {"type": "string", "description": "InChI chemical unique identifier for the current species"},
                                            "InChIKey": {"type": "string", "description": "InChIKey derived from the InChI for the current species"},
                                            "stoichiometricFormula": {"type": "string", "description": "Stoichiometric formula for the current species"},
                                            "massNumber": {"type": "integer", "description": "Mass number for the current species"},
                                            "charge": {"type": "integer", "description": "Electric charge for the current species"},
                                            "speciesType": {"type": "string", "description": "Type (admitted values are 'molecule', 'atom', 'particle') for the current species"},
                                            "structuralFormula": {"type": "string", "description": "Structural formula for the current species"},
                                            "name": {"type": "string", "description": "Human readable species name for the current species"},
                                            "did": {"type": "string", "description": "Alternative unique identifier for the current species"},
                                            "tapEndpoint": {"type": "string", "description": "Database TAP-endpoint URL for the database containing the current species"},
                                            "lastIngestionScriptDate": {"type": "string", "format": "date", "description": "Last ingestion script execution for the database containing the current species"},
                                            "speciesLastSeenOn": {"type": "string", "format": "date", "description": "Last time species was updated for the database containing the current species"},
                                            "# unique atoms": {"type": "integer", "description": "Number of unique atoms in the current species"},
                                            "# total atoms": {"type": "integer", "description": "Total number of atoms in the current species"},
                                            "computed charge": {"type": "integer", "description": "Computed charge for the current species"},
                                            "computed mass number": {"type": "number", "description": "Computed mass number for the current species"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/nodes": {
            "get": {
                "summary": "Get all database nodes",
                "description": (
                    "Gets all the Nodes available on the Species Database.\n"
                    "Returns a list of dictionaries, each containing node information."
                ),
                "responses": {
                    "200": {
                        "description": "A list of dictionaries, each containing node information.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "shortName": {"type": "string", "description": "Short name identifier for the database node"},
                                            "description": {"type": "string", "description": "Descriptive text about the database node"},
                                            "contactEmail": {"type": "string", "description": "Email address for contacting the node maintainer"},
                                            "ivoIdentifier": {"type": "string", "description": "Unique IVO (International Virtual Observatory) identifier for the node"},
                                            "tapEndpoint": {"type": "string", "description": "TAP (Table Access Protocol) endpoint URL for the database node"},
                                            "referenceUrl": {"type": "string", "description": "Reference URL with additional information about the node"},
                                            "lastUpdate": {"type": "string", "format": "date", "description": "Date when the node was last updated"},
                                            "lastSeen": {"type": "string", "format": "date", "description": "Date when the node was last seen/accessed"},
                                            "topics": {"type": "array", "items": {"type": "string"}, "description": "List of strings describing the scientific topics covered by the node"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/server_info": {
            "get": {
                "summary": "Get server info",
                "description": (
                    "Get information about the VAMDC MCP server and available capabilities.\n"
                    "Returns server information including available tools and endpoints."
                ),
                "responses": {
                    "200": {
                        "description": "Server info",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "server_name": {"type": "string"},
                                        "version": {"type": "string"},
                                        "available_tools": {"type": "array", "items": {"type": "string"}},
                                        "description": {"type": "string"},
                                        "endpoints": {
                                            "type": "object",
                                            "properties": {
                                                "species": {"type": "string"},
                                                "nodes": {"type": "string"},
                                                "lines": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/openapi.json": {
            "get": {
                "summary": "OpenAPI specification",
                "description": "Returns the OpenAPI JSON specification for this server.",
                "responses": {
                    "200": {
                        "description": "OpenAPI JSON",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    }
}

class VAMDCHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/mcp/lines":
                lambda_min = float(query.get("lambda_min", [None])[0])
                lambda_max = float(query.get("lambda_max", [None])[0])
                listNodes = query.get("listNodes", None)
                listSpecies = query.get("listSpecies", None)
                result = getLines(lambda_min, lambda_max, listNodes, listSpecies)
                self._send_json(result)
            elif path == "/mcp/species":
                result = getSpecies()
                self._send_json(result)
            elif path == "/mcp/nodes":
                result = getNodes()
                self._send_json(result)
            elif path == "/mcp/server_info":
                result = {
                    "server_name": "VAMDC MCP HTTP Server",
                    "version": "1.0.0",
                    "available_tools": ["lines", "species", "nodes"],
                    "description": "HTTP server for VAMDC MCP",
                    "endpoints": {
                        "species": "Get all available chemical species",
                        "nodes": "Get all available database nodes",
                        "lines": "Get spectral lines within wavelength range",
                        "openapi.json" : "openapi specification for this server"
                    }
                }
                self._send_json(result)
            elif path == "/mcp/openapi.json":
                self._send_json(OPENAPI_SPEC)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def _send_json(self, obj):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj, default=str).encode())

def run_server():
    server = HTTPServer(("0.0.0.0", 8888), VAMDCHandler)
    print("Serving HTTP on 0.0.0.0 port 8888 ...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server.")
        server.server_close()

if __name__ == "__main__":
    run_server()