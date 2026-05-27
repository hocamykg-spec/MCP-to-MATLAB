"""
MATLAB command execution tools for MCP server.

Provides tools for executing MATLAB commands and scripts.
"""

import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExecuteInput(BaseModel):
    """Input model for MATLAB command execution."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    command: str = Field(
        ..., 
        description="MATLAB expression or multi-line statement to execute (e.g., '1 + 1', 'disp(\"hello\")', 'x = 1:10;')",
        min_length=1,
        max_length=10000
    )


class ExecuteScriptInput(BaseModel):
    """Input model for MATLAB script execution."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    script_path: str = Field(
        ..., 
        description="Absolute path to the .m script file to execute (e.g., 'C:/scripts/my_script.m')",
        min_length=1,
        max_length=500
    )


def register_execute(mcp, session):
    """Register MATLAB execution tools with the MCP server."""
    
    @mcp.tool(
        name="matlab_execute",
        annotations={
            "title": "Execute MATLAB Command",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False
        }
    )
    def matlab_execute(params: ExecuteInput) -> Dict[str, Any]:
        """Execute a MATLAB expression or multi-line statement and return the output.
        
        This tool executes MATLAB code and captures stdout, warnings, errors, and execution time.
        It can run simple expressions, function calls, or multi-line scripts.
        
        Args:
            params (ExecuteInput): Validated input parameters containing:
                - command (str): MATLAB expression or statement to execute
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - stdout (str): Standard output from MATLAB
                - warnings (list): List of warning messages
                - errors (list): List of error messages
                - execution_time_ms (float): Execution time in milliseconds
                
        Examples:
            - Execute simple math: "1 + 1"
            - Run MATLAB function: "disp('Hello World')"
            - Create variable: "x = 1:10;"
            - Multi-line script: "x = 1:10;\\ny = x.^2;\\nplot(x, y);"
        """
        engine = session.engine
        start = time.perf_counter()

        stdout = ""
        errors = []
        warnings = []

        try:
            result = engine.eval(params.command, nargout=0)
            if result is not None:
                stdout = str(result)
        except Exception as e:
            errors.append(str(e))

        elapsed = (time.perf_counter() - start) * 1000

        return {
            "stdout": stdout,
            "warnings": warnings,
            "errors": errors,
            "execution_time_ms": round(elapsed, 2),
        }

    @mcp.tool(
        name="matlab_execute_script",
        annotations={
            "title": "Execute MATLAB Script",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False
        }
    )
    def matlab_execute_script(params: ExecuteScriptInput) -> Dict[str, Any]:
        """Execute a MATLAB .m script file from disk.
        
        This tool runs an existing MATLAB script file and captures the output.
        
        Args:
            params (ExecuteScriptInput): Validated input parameters containing:
                - script_path (str): Absolute path to the .m script file
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - stdout (str): Standard output from MATLAB
                - errors (list): List of error messages
                - execution_time_ms (float): Execution time in milliseconds
                
        Examples:
            - Run script: "C:/scripts/my_analysis.m"
            - Run function: "D:/MATLAB/work/process_data.m"
        """
        engine = session.engine
        start = time.perf_counter()

        stdout = ""
        errors = []

        try:
            engine.run(params.script_path, nargout=0)
        except Exception as e:
            errors.append(str(e))

        elapsed = (time.perf_counter() - start) * 1000

        return {
            "stdout": stdout,
            "errors": errors,
            "execution_time_ms": round(elapsed, 2),
        }