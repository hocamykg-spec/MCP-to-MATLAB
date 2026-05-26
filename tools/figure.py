import base64
import tempfile
import os


def register_figure(mcp, session):
    @mcp.tool()
    def matlab_get_figure(
        figure_id: int = 0, format: str = "png"
    ) -> dict:
        """将当前或指定图窗渲染为图片，返回 base64 编码"""
        engine = session.engine
        try:
            if figure_id > 0:
                engine.eval(f"figure({figure_id})", nargout=0)

            fmt = format if format in ("png", "svg") else "png"
            ext = ".svg" if fmt == "svg" else ".png"
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f"matlab_figure_{os.getpid()}.{ext}",
            )

            if fmt == "svg":
                engine.eval(
                    f"print(gcf, '-dsvg', '-painters', '{tmp_path}')",
                    nargout=0,
                )
            else:
                engine.eval(
                    f"print(gcf, '-dpng', '-r150', '{tmp_path}')",
                    nargout=0,
                )

            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    img_bytes = f.read()
                os.remove(tmp_path)
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                return {
                    "image_base64": img_b64,
                    "width": 800,
                    "height": 600,
                    "format": fmt,
                }
            return {"image_base64": "", "width": 0, "height": 0, "format": fmt}
        except Exception:
            return {"image_base64": "", "width": 0, "height": 0, "format": "png"}
