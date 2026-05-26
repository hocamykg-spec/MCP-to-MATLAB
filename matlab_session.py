try:
    import matlab.engine
except ImportError:
    matlab = None  # Placeholder for environments without MATLAB Engine; mocked in tests


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
