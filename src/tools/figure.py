"""
MATLAB figure export tools for MCP server.

Provides tools for exporting MATLAB figures as images.
"""

import base64
import tempfile
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class FigureFormat(str, Enum):
    """Supported figure export formats."""
    PNG = "png"
    SVG = "svg"


class GetFigureInput(BaseModel):
    """Input model for getting a MATLAB figure."""
    model_config = ConfigDict(
        validate_assignment=True
    )

    figure_id: Optional[int] = Field(
        default=0,
        description="MATLAB figure ID to export. 0 (default) means current active figure.",
        ge=0,
        le=100
    )
    format: FigureFormat = Field(
        default=FigureFormat.PNG,
        description="Export format: 'png' (default, raster) or 'svg' (vector)"
    )


def register_figure(mcp, session):
    """Register MATLAB figure export tools with the MCP server."""
    
    @mcp.tool(
        name="matlab_get_figure",
        annotations={
            "title": "Export MATLAB Figure",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    )
    def matlab_get_figure(params: GetFigureInput) -> Dict[str, Any]:
        """Export a MATLAB figure as a base64-encoded image.
        
        This tool renders the current or specified MATLAB figure and returns it
        as a base64-encoded image string. Supports PNG (raster) and SVG (vector) formats.
        
        Args:
            params (GetFigureInput): Validated input parameters containing:
                - figure_id (int): MATLAB figure ID (0 for current figure)
                - format (str): Export format ('png' or 'svg')
                
        Returns:
            Dict[str, Any]: JSON response containing:
                - image_base64 (str): Base64-encoded image data
                - width (int): Image width in pixels
                - height (int): Image height in pixels
                - format (str): Actual format used for export
                
        Examples:
            - Export current figure as PNG: figure_id=0, format="png"
            - Export figure 3 as SVG: figure_id=3, format="svg"
        """
        engine = session.engine
        try:
            # Activate specified figure if ID > 0
            if params.figure_id > 0:
                engine.eval(f"figure({params.figure_id})", nargout=0)

            # Determine format and file extension
            fmt = params.format.value if params.format in FigureFormat else "png"
            ext = ".svg" if fmt == "svg" else ".png"
            
            # Create temporary file path
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f"matlab_figure_{os.getpid()}.{ext}",
            )

            # Export figure to file
            if fmt == "svg":
                engine.eval(
                    f"print(gcf, '-dsvg', '-painters', '{tmp_path}')",
                    nargout=0,
                )
            else:
                engine.eval(
                    f"print(gcf, '-dpng', '-r150', '{tmp_path}')",
                    nargout=0,
                )

            # Read and encode the exported file
            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    img_bytes = f.read()
                os.remove(tmp_path)
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                return {
                    "image_base64": img_b64,
                    "width": 800,
                    "height": 600,
                    "format": fmt,
                }
            
            # Return empty result if no figure was exported
            return {"image_base64": "", "width": 0, "height": 0, "format": fmt}
            
        except Exception as e:
            # Handle errors gracefully
            return {
                "image_base64": "", 
                "width": 0, 
                "height": 0, 
                "format": "png",
                "error": str(e)
            }