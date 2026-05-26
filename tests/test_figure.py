import pytest
from unittest.mock import MagicMock, PropertyMock
from tools.figure import register_figure


class TestMatlabFigure:
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

    def test_get_figure_png_default(self):
        """默认导出 png 格式图表，使用 print 命令写入临时文件"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_figure(mcp, session)

        result = registry["matlab_get_figure"]()
        assert result["format"] == "png"
        assert isinstance(result["image_base64"], str)
        assert isinstance(result["width"], int)
        assert isinstance(result["height"], int)

    def test_get_figure_svg(self):
        """导出 svg 格式图表"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_figure(mcp, session)

        result = registry["matlab_get_figure"](format="svg")
        assert result["format"] == "svg"

    def test_get_figure_no_figure(self):
        """没有图窗时返回空图片"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.side_effect = Exception("No figure")
        register_figure(mcp, session)

        result = registry["matlab_get_figure"]()
        assert result["image_base64"] == ""

    def test_get_figure_specific_id(self):
        """导出指定 ID 的图窗"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_figure(mcp, session)

        result = registry["matlab_get_figure"](figure_id=3)
        assert isinstance(result["width"], int)
        engine.eval.assert_any_call("figure(3)", nargout=0)
