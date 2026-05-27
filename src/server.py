#!/usr/bin/env python3
"""
MCP Server for MATLAB Integration.

This server provides tools to interact with MATLAB via the MATLAB Engine API,
including command execution, variable management, figure export, Simulink control,
and workspace management.
"""

import atexit
from mcp.server.fastmcp import FastMCP
from .matlab_session import MatlabSession
from .config import DEFAULT_CONFIG
from .tools.execute import register_execute
from .tools.variables import register_variables
from .tools.figure import register_figure
from .tools.simulink import register_simulink
from .tools.workspace import register_workspace


def main():
    """Initialize and run the MATLAB MCP server."""
    # Create MATLAB session with configured workspace directory
    session = MatlabSession(workspace_dir=DEFAULT_CONFIG.matlab_workspace_dir)
    atexit.register(session.shutdown)

    # Initialize MCP server with proper naming convention
    mcp = FastMCP("matlab_mcp")

    # Register all tool modules
    register_execute(mcp, session)
    register_variables(mcp, session)
    register_figure(mcp, session)
    register_simulink(mcp, session)
    register_workspace(mcp, session)

    # Run server with stdio transport for local integration
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
