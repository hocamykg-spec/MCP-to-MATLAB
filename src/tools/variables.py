"""
MATLAB variable management tools for MCP server.

Provides tools for reading, writing, and listing MATLAB workspace variables.
"""

import base64
import sys
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

try:
    import numpy as np
except ImportError:
    np = None  # numpy not available; numpy-dependent paths skipped


class GetVariableInput(BaseModel):
    """Input model for getting a MATLAB variable."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    name: str = Field(
        ..., 
        description="Name of the MATLAB workspace variable to retrieve (e.g., 'x', 'my_matrix', 'data')",
        min_length=1,
        max_length=100
    )


class SetVariableInput(BaseModel):
    """Input model for setting a MATLAB variable."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    name: str = Field(
        ..., 
        description="Name for the MATLAB workspace variable (e.g., 'x', 'my_matrix', 'results')",
        min_length=1,
        max_length=100
    )
    value: Union[int, float, str, bool, List[Any]] = Field(
        ..., 
        description="Value to assign. Scalars (int/float/str/bool) are stored directly. Lists are converted to MATLAB arrays/matrices."
    )
    type_hint: str = Field(
        default="auto",
        description="Type hint for the value: 'auto' (default), 'scalar', 'matrix', or 'string'"
    )


def _get_matlab_type_from_value(engine, name):
    """Get the MATLAB class name of a variable."""
    try:
        cls_name = str(engine.eval(f"class({name})"))
        return cls_name
    except Exception:
        return "unknown"


def _get_matlab_size(engine, name):
    """Get the size of a MATLAB variable as a string."""
    try:
        size_str = str(engine.eval(f"mat2str(size({name}))"))
        return size_str
    except Exception:
        return "unknown"


def _serialize_value(engine, name, max_size_kb=1024):
    """Serialize a MATLAB variable for JSON transport."""
    val = engine.workspace.get(name)
    if val is None:
        raise KeyError(f"Variable '{name}' not found in MATLAB workspace")

    # Handle numpy arrays
    if np is not None and isinstance(val, np.ndarray):
        est_bytes = val.nbytes
        if est_bytes > max_size_kb * 1024:
            return None, base64.b64encode(val.tobytes()).decode("utf-8")
        return val.tolist(), None

    # Handle lists
    if isinstance(val, list):
        return val, None

    # Handle scalars and strings
    if isinstance(val, (int, float, str, bool, complex)):
        return val, None

    # Handle other types (encode as base64 if too large)
    est_bytes = sys.getsizeof(val)
    if est_bytes > max_size_kb * 1024:
        encoded = base64.b64encode(str(val).encode()).decode("utf-8")
        return None, encoded
    return str(val), None


def register_variables(mcp, session):
    """Register MATLAB variable management tools with the MCP server."""
    
    @mcp.tool(
        name="matlab_get_variable",
        annotations={
            "title": "Get MATLAB Variable",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    )
    def matlab_get_variable(params: GetVariableInput) -> Dict[str, Any]:
        """Read a variable from the MATLAB workspace.
        
        This tool retrieves a variable's value, type, and dimensions from the MATLAB workspace.
        Small variables are returned as JSON values, large matrices as nested lists,
        and very large variables as base64-encoded strings.
        
        Args:
            params (GetVariableInput): Validated input parameters containing:
                - name (str): Name of the MATLAB variable to retrieve
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - name (str): Variable name
                - value: Variable value (scalar, list, or null if base64-encoded)
                - type (str): MATLAB class name (e.g., 'double', 'char', 'struct')
                - dimensions (str): Variable dimensions as string (e.g., '[3 4]', '[1 10]')
                - base64_bytes (str or null): Base64-encoded bytes for large variables
                
        Examples:
            - Get scalar: name="x" -> {"name": "x", "value": 42.0, "type": "double", ...}
            - Get matrix: name="A" -> {"name": "A", "value": [[1,2],[3,4]], "type": "double", ...}
        """
        engine = session.engine
        try:
            mat_type = _get_matlab_type_from_value(engine, params.name)
            size = _get_matlab_size(engine, params.name)
            value, base64_bytes = _serialize_value(engine, params.name)
            return {
                "name": params.name,
                "value": value,
                "type": mat_type,
                "dimensions": size,
                "base64_bytes": base64_bytes,
            }
        except Exception as e:
            return {
                "name": params.name,
                "value": None,
                "type": "error",
                "dimensions": "",
                "base64_bytes": None,
                "error": str(e)
            }

    @mcp.tool(
        name="matlab_set_variable",
        annotations={
            "title": "Set MATLAB Variable",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    )
    def matlab_set_variable(params: SetVariableInput) -> Dict[str, Any]:
        """Write a Python/JSON value to the MATLAB workspace.
        
        This tool creates or updates a variable in the MATLAB workspace.
        Scalars are stored directly, lists are converted to MATLAB arrays.
        
        Args:
            params (SetVariableInput): Validated input parameters containing:
                - name (str): Name for the MATLAB variable
                - value: Value to assign (scalar or list)
                - type_hint (str): Type hint for conversion ('auto', 'scalar', 'matrix', 'string')
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - ok (bool): Whether the operation succeeded
                - name (str): Variable name that was set
                
        Examples:
            - Set scalar: name="x", value=42 -> {"ok": true, "name": "x"}
            - Set matrix: name="A", value=[[1,2],[3,4]] -> {"ok": true, "name": "A"}
            - Set string: name="msg", value="hello" -> {"ok": true, "name": "msg"}
        """
        engine = session.engine
        try:
            if isinstance(params.value, list) and params.type_hint == "matrix":
                if np is not None:
                    engine.workspace[params.name] = np.array(params.value, dtype=float)
                else:
                    engine.workspace[params.name] = params.value
            elif isinstance(params.value, list):
                if np is not None:
                    engine.workspace[params.name] = np.array(params.value, dtype=float)
                else:
                    engine.workspace[params.name] = params.value
            else:
                engine.workspace[params.name] = params.value
            return {"ok": True, "name": params.name}
        except Exception as e:
            return {"ok": False, "name": params.name, "error": str(e)}

    @mcp.tool(
        name="matlab_list_variables",
        annotations={
            "title": "List MATLAB Variables",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    )
    def matlab_list_variables() -> List[Dict[str, Any]]:
        """List all variables in the MATLAB workspace.
        
        This tool returns information about all variables currently in the MATLAB workspace,
        equivalent to the MATLAB 'whos' command.
        
        Returns:
            List[Dict[str, Any]]: List of variable information dictionaries, each containing:
                - name (str): Variable name
                - type (str): MATLAB class name
                - size (str): Variable dimensions
                - bytes (int): Memory usage in bytes
                
        Example output:
            [
                {"name": "x", "type": "double", "size": "1x10", "bytes": 80},
                {"name": "A", "type": "double", "size": "3x3", "bytes": 72}
            ]
        """
        engine = session.engine
        try:
            raw = str(engine.eval("evalc('whos')"))
            variables = []
            lines = raw.strip().split("\n")
            for line in lines[3:]:
                parts = line.split()
                if len(parts) >= 4:
                    variables.append({
                        "name": parts[0],
                        "type": parts[-1],
                        "size": parts[1],
                        "bytes": int(parts[2]) if parts[2].isdigit() else 0,
                    })
            return variables
        except Exception:
            return []