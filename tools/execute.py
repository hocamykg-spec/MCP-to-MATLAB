import time


def register_execute(mcp, session):
    @mcp.tool()
    def matlab_execute(command: str) -> dict:
        """执行 MATLAB 表达式或多行语句，返回 stdout、warnings、errors 和执行时间"""
        engine = session.engine
        start = time.perf_counter()

        stdout = ""
        errors = []
        warnings = []

        try:
            result = engine.eval(command, nargout=0)
            if result is not None:
                stdout = str(result)
        except Exception as e:
            errors.append(str(e))

        elapsed = (time.perf_counter() - start) * 1000

        return {
            "stdout": stdout,
            "warnings": warnings,
            "errors": errors,
            "execution_time_ms": round(elapsed, 2),
        }

    @mcp.tool()
    def matlab_execute_script(script_path: str) -> dict:
        """运行磁盘上的 .m 脚本文件"""
        engine = session.engine
        start = time.perf_counter()

        stdout = ""
        errors = []

        try:
            engine.run(script_path, nargout=0)
        except Exception as e:
            errors.append(str(e))

        elapsed = (time.perf_counter() - start) * 1000

        return {
            "stdout": stdout,
            "errors": errors,
            "execution_time_ms": round(elapsed, 2),
        }
