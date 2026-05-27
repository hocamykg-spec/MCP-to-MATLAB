import os
import sys

try:
    _MATLAB_ROOT = os.environ.get("MATLAB_ROOT", r"D:\MATLAB")
    os.add_dll_directory(os.path.join(_MATLAB_ROOT, "bin", "win64"))
    os.add_dll_directory(os.path.join(_MATLAB_ROOT, "extern", "bin", "win64"))
    sys.path.insert(0, os.path.join(_MATLAB_ROOT, "extern", "engines", "python", "dist", "matlab", "engine", "win64"))
    sys.path.insert(0, os.path.join(_MATLAB_ROOT, "extern", "bin", "win64"))
    import matlab.engine
except (ImportError, OSError, FileNotFoundError):
    matlab = None


class MatlabSession:
    def __init__(self, workspace_dir: str = "."):
        self._engine = None
        self._workspace_dir = workspace_dir

    @property
    def engine(self):
        if self._engine is None:
            self._engine = matlab.engine.start_matlab()
            if self._workspace_dir != ".":
                self._engine.cd(self._workspace_dir)
        return self._engine

    def restart(self):
        if self._engine is not None:
            self._engine.quit()
        self._engine = None

    def shutdown(self):
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
