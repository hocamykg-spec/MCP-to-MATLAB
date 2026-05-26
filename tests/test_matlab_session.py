import pytest
from unittest.mock import MagicMock, patch
from matlab_session import MatlabSession


class TestMatlabSession:
    def test_lazy_init_does_not_start_engine_on_creation(self):
        """Engine should not start on Session creation, only on first access."""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            mock_matlab.engine.start_matlab.assert_not_called()

    def test_engine_property_starts_engine_once(self):
        """Multiple accesses to engine property should start MATLAB only once."""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            e1 = session.engine
            e2 = session.engine
            mock_matlab.engine.start_matlab.assert_called_once()
            assert e1 is e2

    def test_shutdown_quits_engine(self):
        """shutdown should call engine.quit()."""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            engine = session.engine
            session.shutdown()
            engine.quit.assert_called_once()

    def test_shutdown_when_not_started_does_nothing(self):
        """shutdown should not error when engine was never started."""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            session.shutdown()

    def test_restart_quits_and_creates_new_engine(self):
        """restart should quit old engine and create a new one."""
        with patch("matlab_session.matlab") as mock_matlab:
            mock_matlab.engine.start_matlab.side_effect = [
                MagicMock(), MagicMock()
            ]
            session = MatlabSession()
            e1 = session.engine
            session.restart()
            e2 = session.engine
            e1.quit.assert_called_once()
            assert e1 is not e2

    def test_initial_workspace_dir_is_set_on_startup(self):
        """After starting engine, initial workspace directory should be set."""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession(workspace_dir="/test/path")
            engine = session.engine
            engine.cd.assert_called_with("/test/path")
