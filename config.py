from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    matlab_workspace_dir: str = "."
    execution_timeout_seconds: int = 60
    max_variable_size_kb: int = 1024
    figure_export_format: str = "png"
    figure_default_width: int = 800
    figure_default_height: int = 600


DEFAULT_CONFIG = Config()
