from typing import Any, Optional
from pydantic import BaseModel


class ExecuteResult(BaseModel):
    stdout: str = ""
    warnings: list[str] = []
    errors: list[str] = []
    execution_time_ms: float = 0.0


class ScriptResult(BaseModel):
    stdout: str = ""
    errors: list[str] = []
    execution_time_ms: float = 0.0


class VariableInfo(BaseModel):
    name: str
    type: str
    size: str
    bytes: int


class VariableValue(BaseModel):
    name: str
    value: Any
    type: str
    dimensions: str
    base64_bytes: Optional[str] = None


class SetVariableResult(BaseModel):
    ok: bool
    name: str


class FigureResult(BaseModel):
    image_base64: str
    width: int
    height: int
    format: str


class SimulinkModelInfo(BaseModel):
    name: str
    status: str
    simulation_time: Optional[float] = None


class SimulinkRunResult(BaseModel):
    ok: bool
    simulation_output: Optional[str] = None


class PathResult(BaseModel):
    action: str
    result: list[str]


class WorkspaceResult(BaseModel):
    ok: bool
    action: str
    file_path: Optional[str] = None
