import pytest
from unittest.mock import MagicMock, PropertyMock
from tools.execute import register_execute


class TestMatlabExecute:
    def make_mcp_and_session(self):
        """创建 mock FastMCP 和 mock MatlabSession"""
        mcp = MagicMock()
        mcp_tool_registry = {}

        def mock_tool_decorator():
            def decorator(fn):
                mcp_tool_registry[fn.__name__] = fn
                return fn
            return decorator

        mcp.tool = mock_tool_decorator

        session = MagicMock()
        engine = MagicMock()
        type(session).engine = PropertyMock(return_value=engine)
        engine.eval.return_value = None

        return mcp, session, engine, mcp_tool_registry

    def test_execute_basic_command(self):
        """执行简单命令应返回 stdout"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = "ans = 42"
        register_execute(mcp, session)

        result = registry["matlab_execute"]("1 + 1")
        assert result["stdout"] == "ans = 42"
        assert result["errors"] == []
        engine.eval.assert_called_once()

    def test_execute_returns_execution_time(self):
        """应返回执行时间"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = ""
        register_execute(mcp, session)

        result = registry["matlab_execute"]("disp('hello')")
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] > 0

    def test_execute_matlab_error(self):
        """MATLAB 错误应被捕获并放入 errors 列表"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        error = Exception("Undefined function 'foo'")
        engine.eval.side_effect = error
        register_execute(mcp, session)

        result = registry["matlab_execute"]("foo()")
        assert result["errors"] != []
        assert "Undefined function" in result["errors"][0]

    def test_execute_with_warnings(self):
        """MATLAB 输出中的警告文本应出现在 stdout 中"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = "Warning: Name is nonexistent or not a directory"
        register_execute(mcp, session)

        result = registry["matlab_execute"]("addpath('nonexistent')")
        assert "Warning" in result["stdout"]

    def test_execute_script_runs_m_file(self):
        """execute_script 应运行 .m 文件"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_execute(mcp, session)

        result = registry["matlab_execute_script"]("C:/scripts/test.m")
        engine.run.assert_called_with("C:/scripts/test.m", nargout=0)
