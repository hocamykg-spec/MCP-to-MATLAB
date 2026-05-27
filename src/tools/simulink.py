"""
MATLAB Simulink tools for MCP server.

Provides tools for listing and running Simulink models.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class SimulinkRunInput(BaseModel):
    """Input model for running a Simulink model."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    model_name: str = Field(
        ..., 
        description="Name of the Simulink model to run (e.g., 'my_model', 'sldemo_suspn')",
        min_length=1,
        max_length=100
    )
    stop_time: float = Field(
        default=10.0,
        description="Simulation stop time in seconds (default: 10.0)",
        ge=0.0,
        le=10000.0
    )
    params: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional dictionary of model parameters to set before simulation"
    )


def register_simulink(mcp, session):
    """Register Simulink tools with the MCP server."""
    
    @mcp.tool(
        name="matlab_simulink_list",
        annotations={
            "title": "List Simulink Models",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    )
    def matlab_simulink_list() -> List[Dict[str, Any]]:
        """List all currently open Simulink models.
        
        This tool returns information about all Simulink models that are currently
        open in the MATLAB session.
        
        Returns:
            List[Dict[str, Any]]: List of model information dictionaries, each containing:
                - name (str): Model name
                - status (str): Current simulation status (e.g., 'stopped', 'running', 'paused')
                - simulation_time (float or null): Current simulation time
                
        Example output:
            [
                {"name": "my_model", "status": "stopped", "simulation_time": null},
                {"name": "sldemo_suspn", "status": "running", "simulation_time": 2.5}
            ]
        """
        engine = session.engine
        try:
            raw = str(engine.eval("evalc('bdroot')"))
            models = [m.strip() for m in raw.split() if m.strip()]
            result = []
            for name in models:
                status = str(engine.eval(f"get_param('{name}', 'SimulationStatus')"))
                result.append({
                    "name": name,
                    "status": status,
                    "simulation_time": None,
                })
            return result
        except Exception as e:
            return [{"name": str(e), "status": "error", "simulation_time": None}]

    @mcp.tool(
        name="matlab_simulink_run",
        annotations={
            "title": "Run Simulink Simulation",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False
        }
    )
    def matlab_simulink_run(params: SimulinkRunInput) -> Dict[str, Any]:
        """Run a Simulink model simulation.
        
        This tool runs a Simulink model with the specified parameters and stop time.
        It can optionally set model parameters before starting the simulation.
        
        Args:
            params (SimulinkRunInput): Validated input parameters containing:
                - model_name (str): Name of the Simulink model
                - stop_time (float): Simulation stop time in seconds
                - params (dict or None): Optional model parameters to set
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - ok (bool): Whether the simulation completed successfully
                - simulation_output (str or null): Simulation output or error message
                
        Examples:
            - Run model: model_name="my_model" -> {"ok": true, "simulation_output": null}
            - Run with params: model_name="my_model", stop_time=5.0, params={"Gain": "2"}
        """
        engine = session.engine
        try:
            # Set optional parameters
            if params.params:
                for key, value in params.params.items():
                    engine.eval(
                        f"set_param('{params.model_name}', '{key}', '{value}')", nargout=0
                    )
            
            # Set stop time
            engine.eval(f"set_param('{params.model_name}', 'StopTime', '{params.stop_time}')", nargout=0)
            
            # Run simulation
            engine.eval(f"sim('{params.model_name}')", nargout=0)
            
            return {"ok": True, "simulation_output": None}
            
        except Exception as e:
            return {"ok": False, "simulation_output": str(e)}