# MCP-MATLAB 服务实施计划

> **面向执行代理：** 必选子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐步实现。步骤使用 checkbox（`- [ ]`）语法跟踪。

**目标：** 构建一个基于 Python FastMCP 的 stdio MCP 服务器，通过 MATLAB Engine API 让 Claude Code 全面操作本地 MATLAB。

**架构：** 单 Python 进程，FastMCP 提供 10 个 Tool，MatlabSession 懒加载单例管理 matlab.engine 连接。每个 tool 文件通过 `register(mcp, session)` 模式注入依赖，便于测试。

**技术栈：** Python 3.9+、FastMCP (mcp[cli])、matlab.engine、numpy、pytest

---

## 文件职责

| 文件 | 职责 |
|------|------|
| `pyproject.toml` | 项目元信息与依赖声明 |
| `config.py` | 超时、缓冲上限、图表格式等可配参数 |
| `schemas.py` | Tool 返回值的 Pydantic 模型，统一输出结构 |
| `matlab_session.py` | Engine 懒加载、崩溃重启、优雅关闭 |
| `tools/execute.py` | matlab_execute / matlab_execute_script |
| `tools/variables.py` | get / set / list_variable |
| `tools/figure.py` | get_figure：内存中渲染图表为 base64 |
| `tools/simulink.py` | simulink_list / simulink_run |
| `tools/workspace.py` | path_manage / workspace_manage |
| `server.py` | FastMCP 入口：创建 session，注册所有 tool，`mcp.run(transport="stdio")` |
| `.claude/mcp.json` | Claude Code 连接配置 |
| `tests/` | 全部 10 个 Tool + session 生命周期单元测试（mock engine） |

---

### Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `config.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "mcp-matlab"
version = "0.1.0"
description = "MCP server connecting Claude Code to MATLAB via Engine API"
requires-python = ">=3.9"
dependencies = [
    "mcp[cli]>=1.0.0",
    "numpy>=1.21",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.12.0",
]
```

- [ ] **Step 2: 创建 config.py**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    matlab_workspace_dir: str = "."
    execution_timeout_seconds: int = 60
    max_variable_size_kb: int = 1024
    figure_export_format: str = "png"
    figure_default_width: int = 800
    figure_default_height: int = 600


DEFAULT_CONFIG = Config()
```

- [ ] **Step 3: 安装依赖**

```bash
pip install -e ".[dev]"
```

Expected: 成功安装 mcp、numpy、pytest、pytest-mock

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml config.py
git commit -m "feat: 初始化项目结构与配置"
```

---

### Task 2: 输出 Schema

**Files:**
- Create: `schemas.py`

- [ ] **Step 1: 创建 schemas.py**

```python
from typing import Any, Optional
from pydantic import BaseModel


class ExecuteResult(BaseModel):
    stdout: str = ""
    warnings: list[str] = []
    errors: list[str] = []
    execution_time_ms: float = 0.0


class ScriptResult(BaseModel):
    stdout: str = ""
    errors: list[str] = []
    execution_time_ms: float = 0.0


class VariableInfo(BaseModel):
    name: str
    type: str
    size: str
    bytes: int


class VariableValue(BaseModel):
    name: str
    value: Any
    type: str
    dimensions: str
    base64_bytes: Optional[str] = None


class SetVariableResult(BaseModel):
    ok: bool
    name: str


class FigureResult(BaseModel):
    image_base64: str
    width: int
    height: int
    format: str


class SimulinkModelInfo(BaseModel):
    name: str
    status: str
    simulation_time: Optional[float] = None


class SimulinkRunResult(BaseModel):
    ok: bool
    simulation_output: Optional[str] = None


class PathResult(BaseModel):
    action: str
    result: list[str]


class WorkspaceResult(BaseModel):
    ok: bool
    action: str
    file_path: Optional[str] = None
```

- [ ] **Step 2: 运行 Python 做语法检查**

```bash
python -c "from schemas import ExecuteResult; print(ExecuteResult(stdout='ok').model_dump())"
```

Expected: `{'stdout': 'ok', 'warnings': [], 'errors': [], 'execution_time_ms': 0.0}`

- [ ] **Step 3: 提交**

```bash
git add schemas.py
git commit -m "feat: 添加 Pydantic 输出 Schema"
```

---

### Task 3: MatlabSession 连接管理

**Files:**
- Create: `matlab_session.py`
- Create: `tests/test_matlab_session.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_matlab_session.py
import pytest
from unittest.mock import MagicMock, patch
from matlab_session import MatlabSession


class TestMatlabSession:
    def test_lazy_init_does_not_start_engine_on_creation(self):
        """Engine 不应该在创建 Session 时启动，仅在首次访问时启动"""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            mock_matlab.engine.start_matlab.assert_not_called()

    def test_engine_property_starts_engine_once(self):
        """多次访问 engine 属性只应启动一次 MATLAB"""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            e1 = session.engine
            e2 = session.engine
            mock_matlab.engine.start_matlab.assert_called_once()
            assert e1 is e2

    def test_shutdown_quits_engine(self):
        """shutdown 应调用 engine.quit()"""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            engine = session.engine  # 触发启动
            session.shutdown()
            engine.quit.assert_called_once()

    def test_shutdown_when_not_started_does_nothing(self):
        """未启动 engine 时 shutdown 不应报错"""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession()
            session.shutdown()  # 不应抛异常

    def test_restart_quits_and_creates_new_engine(self):
        """restart 应退出旧 engine 并创建新的"""
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
        """启动 engine 后应设置初始工作目录"""
        with patch("matlab_session.matlab") as mock_matlab:
            session = MatlabSession(workspace_dir="/test/path")
            engine = session.engine
            engine.cd.assert_called_with("/test/path")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_matlab_session.py -v
```

Expected: 全部 FAIL（ImportError / ModuleNotFoundError）

- [ ] **Step 3: 实现 MatlabSession**

```python
# matlab_session.py
import matlab.engine


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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_matlab_session.py -v
```

Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add matlab_session.py tests/test_matlab_session.py
git commit -m "feat: 添加 MatlabSession 懒加载单例连接管理"
```

---

### Task 4: 命令执行 Tool

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/execute.py`
- Create: `tests/test_execute.py`

- [ ] **Step 1: 创建 tools/__init__.py**

```python
# tools/__init__.py
```

- [ ] **Step 2: 编写失败测试**

```python
# tests/test_execute.py
import pytest
from unittest.mock import MagicMock, PropertyMock
from tools.execute import register_execute


class TestMatlabExecute:
    def make_mcp_and_session(self):
        """创建 mock FastMCP 和 mock MathlabSession"""
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
        engine.eval.return_value = None  # 默认无返回值

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
        """execut_script 应运行 .m 文件"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_execute(mcp, session)

        result = registry["matlab_execute_script"]("C:/scripts/test.m")
        engine.run.assert_called_with("C:/scripts/test.m", nargout=0)
```

- [ ] **Step 3: 运行测试确认失败**

```bash
pytest tests/test_execute.py -v
```

Expected: 全部 FAIL

- [ ] **Step 4: 实现 tools/execute.py**

```python
# tools/execute.py
import time
from schemas import ExecuteResult


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
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_execute.py -v
```

Expected: 5 passed

- [ ] **Step 6: 提交**

```bash
git add tools/__init__.py tools/execute.py tests/test_execute.py
git commit -m "feat: 添加 matlab_execute 和 matlab_execute_script Tool"
```

---

### Task 5: 变量操作 Tool

**Files:**
- Create: `tools/variables.py`
- Create: `tests/test_variables.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_variables.py
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
        engine.workspace = {"big": b"\x00" * 200000}  # ~200KB
        register_variables(mcp, session)

        result = registry["matlab_get_variable"]("big")
        assert result["base64_bytes"] is not None
        assert result["value"] is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_variables.py -v
```

Expected: 全部 FAIL

- [ ] **Step 3: 实现 tools/variables.py**

```python
# tools/variables.py
import base64
import sys


def _get_matlab_type_from_value(engine, name):
    try:
        cls_name = str(engine.eval(f"class({name})"))
        return cls_name
    except Exception:
        return "unknown"


def _get_matlab_size(engine, name):
    try:
        size_str = str(engine.eval(f"mat2str(size({name}))"))
        return size_str
    except Exception:
        return "unknown"


def _serialize_value(engine, name, max_size_kb=1024):
    val = engine.workspace.get(name)
    if val is None:
        return None, None

    import numpy as np

    if isinstance(val, (np.ndarray, list)):
        if isinstance(val, np.ndarray):
            est_bytes = val.nbytes
            if est_bytes > max_size_kb * 1024:
                return None, base64.b64encode(val.tobytes()).decode("utf-8")
            return val.tolist(), None
        return val, None

    if isinstance(val, (int, float, str, bool, complex)):
        return val, None

    est_bytes = sys.getsizeof(val)
    if est_bytes > max_size_kb * 1024:
        encoded = base64.b64encode(str(val).encode()).decode("utf-8")
        return None, encoded
    return str(val), None


def register_variables(mcp, session):
    @mcp.tool()
    def matlab_get_variable(name: str) -> dict:
        """读取 MATLAB 工作区变量，标量返回 JSON 值，矩阵返回嵌套列表，大变量返回 base64"""
        engine = session.engine
        try:
            mat_type = _get_matlab_type_from_value(engine, name)
            size = _get_matlab_size(engine, name)
            value, base64_bytes = _serialize_value(engine, name)
            return {
                "name": name,
                "value": value,
                "type": mat_type,
                "dimensions": size,
                "base64_bytes": base64_bytes,
            }
        except Exception as e:
            return {
                "name": name,
                "value": None,
                "type": "",
                "dimensions": "",
                "base64_bytes": None,
            }

    @mcp.tool()
    def matlab_set_variable(name: str, value, type_hint: str = "auto") -> dict:
        """将 Python/JSON 值写入 MATLAB 工作区"""
        import numpy as np

        engine = session.engine
        try:
            if type_hint == "matrix" and isinstance(value, list):
                mat_value = np.array(value, dtype=float)
                engine.workspace[name] = mat_value
            elif isinstance(value, list):
                mat_value = np.array(value, dtype=float)
                engine.workspace[name] = mat_value
            else:
                engine.workspace[name] = value
            return {"ok": True, "name": name}
        except Exception as e:
            return {"ok": False, "name": name}

    @mcp.tool()
    def matlab_list_variables() -> list:
        """列出工作区所有变量，等价于 MATLAB whos()"""
        engine = session.engine
        try:
            raw = str(engine.eval("evalc('whos')"))
            variables = []
            lines = raw.strip().split("\n")
            for line in lines[3:]:  # 跳过 whos 输出的表头
                parts = line.split()
                if len(parts) >= 4:
                    variables.append({
                        "name": parts[0],
                        "type": parts[-1],
                        "size": parts[1],
                        "bytes": int(parts[2]) if parts[2].isdigit() else 0,
                    })
            return variables
        except Exception as e:
            return [{"name": str(e), "type": "error", "size": "", "bytes": 0}]
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_variables.py -v
```

Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add tools/variables.py tests/test_variables.py
git commit -m "feat: 添加变量读写与列表 Tool"
```

---

### Task 6: 图表导出 Tool

**Files:**
- Create: `tools/figure.py`
- Create: `tests/test_figure.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_figure.py
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
        # 无图窗时 print 可能失败，返回空图片
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_figure.py -v
```

Expected: 全部 FAIL

- [ ] **Step 3: 实现 tools/figure.py**

```python
# tools/figure.py
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
```

- [ ] **Step 4: 运行测试确认通过**（测试 mock engine，不依赖真实 MATLAB）

```bash
pytest tests/test_figure.py -v
```

Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add tools/figure.py tests/test_figure.py
git commit -m "feat: 添加 get_figure 图表导出 Tool"
```

---

### Task 7: Simulink Tool

**Files:**
- Create: `tools/simulink.py`
- Create: `tests/test_simulink.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_simulink.py
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
        """列出已打开的 Simulink 模型"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = "model1.slx  model2.slx"
        register_simulink(mcp, session)

        result = registry["matlab_simulink_list"]()
        assert isinstance(result, list)

    def test_simulink_run_with_stop_time(self):
        """运行仿真并指定停止时间"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_simulink(mcp, session)

        result = registry["matlab_simulink_run"]("test_model", stop_time=10.0)
        assert result["ok"] is True

    def test_simulink_run_nonexistent_model(self):
        """运行不存在的模型应报错"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.side_effect = Exception("No such model")
        register_simulink(mcp, session)

        result = registry["matlab_simulink_run"]("no_model")
        assert result["ok"] is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_simulink.py -v
```

Expected: 全部 FAIL

- [ ] **Step 3: 实现 tools/simulink.py**

```python
# tools/simulink.py


def register_simulink(mcp, session):
    @mcp.tool()
    def matlab_simulink_list() -> list:
        """列出所有已打开的 Simulink 模型"""
        engine = session.engine
        try:
            raw = str(engine.eval("evalc('bdroot')"))
            models = [m.strip() for m in raw.split() if m.strip()]
            result = []
            for name in models:
                status = str(engine.eval(f"get_param('{name}', 'SimulationStatus')"))
                result.append({
                    "name": name,
                    "status": status,
                    "simulation_time": None,
                })
            return result
        except Exception as e:
            return [{"name": str(e), "status": "error", "simulation_time": None}]

    @mcp.tool()
    def matlab_simulink_run(
        model_name: str, stop_time: float = 10.0, params: dict = None
    ) -> dict:
        """运行 Simulink 模型仿真"""
        import matlab.engine

        engine = session.engine
        try:
            if params:
                for key, value in (params or {}).items():
                    engine.eval(
                        f"set_param('{model_name}', '{key}', '{value}')", nargout=0
                    )

            engine.eval(f"set_param('{model_name}', 'StopTime', '{stop_time}')", nargout=0)
            engine.eval(f"sim('{model_name}')", nargout=0)
            return {"ok": True, "simulation_output": None}
        except Exception as e:
            return {"ok": False, "simulation_output": str(e)}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_simulink.py -v
```

Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add tools/simulink.py tests/test_simulink.py
git commit -m "feat: 添加 Simulink 模型列表与仿真运行 Tool"
```

---

### Task 8: 工作区与路径管理 Tool

**Files:**
- Create: `tools/workspace.py`
- Create: `tests/test_workspace.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_workspace.py
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
        """添加路径到 MATLAB 搜索路径"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)

        result = registry["matlab_path_manage"]("add", "/my/path")
        assert result["action"] == "add"

    def test_path_remove(self):
        """从 MATLAB 搜索路径移除"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)

        result = registry["matlab_path_manage"]("remove", "/my/path")
        assert result["action"] == "remove"

    def test_path_list(self):
        """列出 MATLAB 搜索路径"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        engine.eval.return_value = "/path1;/path2;/path3"
        register_workspace(mcp, session)

        result = registry["matlab_path_manage"]("list")
        assert result["action"] == "list"

    def test_workspace_save_and_load(self):
        """保存和加载工作区"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)

        result_save = registry["matlab_workspace_manage"]("save", "backup.mat")
        assert result_save["ok"] is True

        result_load = registry["matlab_workspace_manage"]("load", "backup.mat")
        assert result_load["ok"] is True

    def test_workspace_clear(self):
        """清空工作区"""
        mcp, session, engine, registry = self.make_mcp_and_session()
        register_workspace(mcp, session)

        result = registry["matlab_workspace_manage"]("clear")
        assert result["ok"] is True
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_workspace.py -v
```

Expected: 全部 FAIL

- [ ] **Step 3: 实现 tools/workspace.py**

```python
# tools/workspace.py


def register_workspace(mcp, session):
    @mcp.tool()
    def matlab_path_manage(action: str, path: str = "") -> dict:
        """管理 MATLAB 搜索路径：add、remove、list"""
        engine = session.engine
        try:
            if action == "add" and path:
                engine.eval(f"addpath('{path}')", nargout=0)
                return {"action": "add", "result": [path]}
            elif action == "remove" and path:
                engine.eval(f"rmpath('{path}')", nargout=0)
                return {"action": "remove", "result": [path]}
            elif action == "list":
                raw = str(engine.eval("path"))
                paths = raw.split(";")
                return {"action": "list", "result": paths}
            else:
                return {"action": action, "result": []}
        except Exception as e:
            return {"action": action, "result": [str(e)]}

    @mcp.tool()
    def matlab_workspace_manage(action: str, file_path: str = "") -> dict:
        """管理工作区：clear、save、load"""
        engine = session.engine
        try:
            if action == "clear":
                engine.eval("clear all", nargout=0)
                return {"ok": True, "action": "clear", "file_path": None}
            elif action == "save" and file_path:
                engine.eval(f"save('{file_path}')", nargout=0)
                return {"ok": True, "action": "save", "file_path": file_path}
            elif action == "load" and file_path:
                engine.eval(f"load('{file_path}')", nargout=0)
                return {"ok": True, "action": "load", "file_path": file_path}
            else:
                return {"ok": False, "action": action, "file_path": file_path}
        except Exception as e:
            return {"ok": False, "action": action, "file_path": str(e)}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_workspace.py -v
```

Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add tools/workspace.py tests/test_workspace.py
git commit -m "feat: 添加路径管理与工作区管理 Tool"
```

---

### Task 9: 服务入口与 MCP 配置

**Files:**
- Create: `server.py`
- Create: `.claude/mcp.json`
- Modify: `config.py`

- [ ] **Step 1: 创建 .claude/mcp.json**

```json
{
  "mcpServers": {
    "matlab": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "C:/Users/vanke/Desktop/mcp-matlab"
    }
  }
}
```

- [ ] **Step 2: 创建 server.py**

```python
# server.py
import sys
import atexit
from mcp.server.fastmcp import FastMCP
from matlab_session import MatlabSession
from config import DEFAULT_CONFIG
from tools.execute import register_execute
from tools.variables import register_variables
from tools.figure import register_figure
from tools.simulink import register_simulink
from tools.workspace import register_workspace


def main():
    session = MatlabSession(workspace_dir=DEFAULT_CONFIG.matlab_workspace_dir)
    atexit.register(session.shutdown)

    mcp = FastMCP("matlab")

    register_execute(mcp, session)
    register_variables(mcp, session)
    register_figure(mcp, session)
    register_simulink(mcp, session)
    register_workspace(mcp, session)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 语法检查**

```bash
python -c "import ast; ast.parse(open('server.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 运行全部单元测试**

```bash
pytest tests/ -v
```

Expected: 全部通过（~24 tests）

- [ ] **Step 5: 提交**

```bash
git add server.py .claude/mcp.json
git commit -m "feat: 添加 FastMCP 服务入口与 Claude Code 配置"
```

---

### Task 10: 集成验证

**Files:**
- No new files

- [ ] **Step 1: 确认 matlab.engine 已安装**

```bash
python -c "import matlab.engine; print('OK')"
```

Expected: `OK`（如果失败则需手动安装 `matlab.engine` 包）

- [ ] **Step 2: 启动服务并验证进程不崩溃**

```bash
timeout 5 python server.py 2>&1 || true
```

Expected: 无崩溃（stdio 模式会等待输入，timeout 正常终止）

- [ ] **Step 3: 用 MCP Inspector 验证协议**

```bash
npx @modelcontextprotocol/inspector python server.py
```

在浏览器中查看所有 10 个 Tool 是否注册成功，测试 `matlab_execute("1+1")`

- [ ] **Step 4: Claude Code 中测试**

在 `.claude/mcp.json` 配置后重启 Claude Code，测试：
```
matlab_execute: "x = 1:10; y = x.^2; plot(x, y)"
matlab_get_variable: "y"
matlab_get_figure: format="png"
matlab_list_variables
```

- [ ] **Step 5: 提交（如有调整）**

```bash
git add -A
git commit -m "chore: 集成验证通过后的最终调整"
```
