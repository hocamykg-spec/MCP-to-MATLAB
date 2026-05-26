import pytest
from unittest.mock import MagicMock, PropertyMock
from tools.simulink import register_simulink


class TestMatlabSimulink:
    def make_mcp_and_session(self):
        mcp = MagicMock()
        mcp_tool_registry = {}

        def mock_tool():
            def decorator(fn):
                mcp_tool_registry[fn.__name__] = fn
                return fn
            return decorator

        mcp.tool = mock_tool
        session = MagicMock()
        engine = MagicMock()
        type(session).engine = PropertyMock(return_value=engine)
        return mcp, session, engine, mcp_tool_registry

    def test_simulink_list_returns_models(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = "model1.slx  model2.slx"
        register_simulink(mcp, session)
        result = registry["matlab_simulink_list"]()
        assert isinstance(result, list)

    def test_simulink_run_with_stop_time(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_simulink(mcp, session)
        result = registry["matlab_simulink_run"]("test_model", stop_time=10.0)
        assert result["ok"] is True

    def test_simulink_run_nonexistent_model(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.side_effect = Exception("No such model")
        register_simulink(mcp, session)
        result = registry["matlab_simulink_run"]("no_model")
        assert result["ok"] is False
