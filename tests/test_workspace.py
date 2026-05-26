import pytest
from unittest.mock import MagicMock, PropertyMock
from tools.workspace import register_workspace


class TestMatlabWorkspace:
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

    def test_path_add(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)
        result = registry["matlab_path_manage"]("add", "/my/path")
        assert result["action"] == "add"

    def test_path_remove(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)
        result = registry["matlab_path_manage"]("remove", "/my/path")
        assert result["action"] == "remove"

    def test_path_list(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = "/path1;/path2;/path3"
        register_workspace(mcp, session)
        result = registry["matlab_path_manage"]("list")
        assert result["action"] == "list"

    def test_workspace_save_and_load(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)
        result_save = registry["matlab_workspace_manage"]("save", "backup.mat")
        assert result_save["ok"] is True
        result_load = registry["matlab_workspace_manage"]("load", "backup.mat")
        assert result_load["ok"] is True

    def test_workspace_clear(self):
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)
        result = registry["matlab_workspace_manage"]("clear")
        assert result["ok"] is True
