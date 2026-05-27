"""
MATLAB workspace and path management tools for MCP server.

Provides tools for managing MATLAB search path and workspace variables.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class PathAction(str, Enum):
    """Supported path management actions."""
    ADD = "add"
    REMOVE = "remove"
    LIST = "list"


class WorkspaceAction(str, Enum):
    """Supported workspace management actions."""
    CLEAR = "clear"
    SAVE = "save"
    LOAD = "load"


class PathManageInput(BaseModel):
    """Input model for MATLAB path management."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    action: PathAction = Field(
        ..., 
        description="Action to perform: 'add' (add path), 'remove' (remove path), or 'list' (list all paths)"
    )
    path: Optional[str] = Field(
        default="",
        description="Directory path to add or remove (required for 'add' and 'remove' actions)",
        max_length=500
    )


class WorkspaceManageInput(BaseModel):
    """Input model for MATLAB workspace management."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    action: WorkspaceAction = Field(
        ..., 
        description="Action to perform: 'clear' (clear all variables), 'save' (save workspace), or 'load' (load workspace)"
    )
    file_path: Optional[str] = Field(
        default="",
        description="File path for save/load operations (required for 'save' and 'load' actions)",
        max_length=500
    )


def register_workspace(mcp, session):
    """Register workspace and path management tools with the MCP server."""
    
    @mcp.tool(
        name="matlab_path_manage",
        annotations={
            "title": "Manage MATLAB Path",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    )
    def matlab_path_manage(params: PathManageInput) -> Dict[str, Any]:
        """Manage the MATLAB search path.
        
        This tool adds, removes, or lists directories in the MATLAB search path.
        The search path determines where MATLAB looks for functions and files.
        
        Args:
            params (PathManageInput): Validated input parameters containing:
                - action (str): Action to perform ('add', 'remove', or 'list')
                - path (str): Directory path for add/remove actions
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - action (str): Action that was performed
                - result (list): List of affected paths
                
        Examples:
            - Add path: action="add", path="C:/my_functions" -> {"action": "add", "result": ["C:/my_functions"]}
            - List paths: action="list" -> {"action": "list", "result": ["C:/MATLAB/work", "C:/my_functions"]}
        """
        engine = session.engine
        try:
            if params.action == PathAction.ADD and params.path:
                engine.eval(f"addpath('{params.path}')", nargout=0)
                return {"action": "add", "result": [params.path]}
            elif params.action == PathAction.REMOVE and params.path:
                engine.eval(f"rmpath('{params.path}')", nargout=0)
                return {"action": "remove", "result": [params.path]}
            elif params.action == PathAction.LIST:
                raw = str(engine.eval("path"))
                paths = raw.split(";")
                return {"action": "list", "result": paths}
            else:
                return {"action": params.action.value, "result": []}
        except Exception as e:
            return {"action": params.action.value, "result": [str(e)]}

    @mcp.tool(
        name="matlab_workspace_manage",
        annotations={
            "title": "Manage MATLAB Workspace",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False
        }
    )
    def matlab_workspace_manage(params: WorkspaceManageInput) -> Dict[str, Any]:
        """Manage the MATLAB workspace variables.
        
        This tool clears, saves, or loads MATLAB workspace variables.
        The workspace contains all variables created during a MATLAB session.
        
        Args:
            params (WorkspaceManageInput): Validated input parameters containing:
                - action (str): Action to perform ('clear', 'save', or 'load')
                - file_path (str): File path for save/load operations
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - ok (bool): Whether the operation succeeded
                - action (str): Action that was performed
                - file_path (str or null): File path used for save/load
                
        Examples:
            - Clear workspace: action="clear" -> {"ok": true, "action": "clear", "file_path": null}
            - Save workspace: action="save", file_path="C:/data/workspace.mat" -> {"ok": true, ...}
            - Load workspace: action="load", file_path="C:/data/workspace.mat" -> {"ok": true, ...}
        """
        engine = session.engine
        try:
            if params.action == WorkspaceAction.CLEAR:
                engine.eval("clear all", nargout=0)
                return {"ok": True, "action": "clear", "file_path": None}
            elif params.action == WorkspaceAction.SAVE and params.file_path:
                engine.eval(f"save('{params.file_path}')", nargout=0)
                return {"ok": True, "action": "save", "file_path": params.file_path}
            elif params.action == WorkspaceAction.LOAD and params.file_path:
                engine.eval(f"load('{params.file_path}')", nargout=0)
                return {"ok": True, "action": "load", "file_path": params.file_path}
            else:
                return {"ok": False, "action": params.action.value, "file_path": params.file_path}
        except Exception as e:
            return {"ok": False, "action": params.action.value, "file_path": str(e)}