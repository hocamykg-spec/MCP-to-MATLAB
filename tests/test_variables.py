import pytest
from unittest.mock import MagicMock, PropertyMock
from tools.variables import register_variables


class TestMatlabVariables:
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

    def test_get_variable_scalar(self):
        """读取标量变量应返回 JSON 数值"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.workspace = {"x": 42.0}
        engine.eval.return_value = "double"
        register_variables(mcp, session)

        result = registry["matlab_get_variable"]("x")
        assert result["value"] == 42.0
        assert result["type"] == "double"
        assert result["name"] == "x"

    def test_get_variable_nonexistent(self):
        """读取不存在的变量应报错"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.workspace = {}
        register_variables(mcp, session)

        result = registry["matlab_get_variable"]("no_such_var")
        assert result["value"] is None
        assert result["type"] == ""

    def test_set_variable_scalar(self):
        """写入标量到 MATLAB 工作区"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_variables(mcp, session)

        result = registry["matlab_set_variable"]("a", 3.14)
        assert result["ok"] is True
        assert result["name"] == "a"

    def test_set_variable_matrix(self):
        """写入矩阵到 MATLAB 工作区"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_variables(mcp, session)

        result = registry["matlab_set_variable"](
            "M", [[1, 2], [3, 4]], type_hint="matrix"
        )
        assert result["ok"] is True

    def test_list_variables(self):
        """列出工作区变量"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = "  Name      Size            Bytes  Class\n  x         1x1                 8  double"
        register_variables(mcp, session)

        result = registry["matlab_list_variables"]()
        assert isinstance(result, list)

    def test_get_variable_large_base64(self):
        """大变量应使用 base64 编码"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        # Use a value large enough to exceed the 1024 KB threshold (~1 MB)
        engine.workspace = {"big": b"\x00" * 2_000_000}
        register_variables(mcp, session)

        result = registry["matlab_get_variable"]("big")
        assert result["base64_bytes"] is not None
        assert result["value"] is None
