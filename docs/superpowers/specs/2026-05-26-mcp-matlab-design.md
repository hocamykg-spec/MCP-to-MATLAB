# MCP-MATLAB 服务设计文档

**日期：** 2026-05-26
**状态：** 已批准

## 概述

基于 stdio 传输的 MCP（Model Context Protocol）服务器，通过 MATLAB Engine API for Python 连接 Claude Code 与本地 MATLAB。提供完整的 MATLAB 代理能力：命令执行、变量读写、图表导出、Simulink 控制、路径与工作区管理。

## 架构

```
Claude Code (stdio)
       | JSON-RPC
       v
+-----------------------+
|  mcp-matlab-server    |  Python FastMCP, 10 个 Tool
+-----------------------+
|  MatlabSession        |  matlab.engine.start_matlab()
|  (懒加载单例)          |  整个会话持久连接
+-----------------------+
       | Python C API
       v
+-----------------------+
|  MATLAB Runtime       |  用户本地 MATLAB
+-----------------------+
```

单 Python 进程。无多进程，无 HTTP 服务器。

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.9+ | `matlab.engine` 仅支持 Python |
| MCP SDK | `mcp[cli]` (FastMCP) | 官方库，原生支持 stdio、自动 JSON-RPC |
| MATLAB API | `matlab.engine` | 功能最全，支持命令/图表/Simulink |
| 数 据 | `numpy` | MATLAB 矩阵/数组与 Python 互转 |
| 传 输 | stdio | 最简单，Claude Code 默认方式 |

## 项目结构

```
mcp-matlab/
├── server.py              # 入口：FastMCP 实例 + 注册所有 Tool
├── matlab_session.py      # MatlabSession：连接管理、懒加载、优雅退出
├── tools/
│   ├── __init__.py
│   ├── execute.py         # matlab_execute、matlab_execute_script
│   ├── variables.py       # get/set/list_variable
│   ├── figure.py          # get_figure
│   ├── simulink.py        # simulink_list、simulink_run
│   └── workspace.py       # path_manage、workspace_manage
├── config.py              # 超时、工作目录、缓冲上限等配置
├── schemas.py             # Pydantic 输出模型
├── pyproject.toml         # 项目元信息与依赖
├── tests/                 # 单元测试 + 集成测试
├── .claude/
│   └── mcp.json           # Claude Code MCP 配置
└── README.md
```

## MCP Tool 清单（10 个）

### 命令执行
1. `matlab_execute(command: str)` → `{stdout, warnings, errors, execution_time_ms}`
   - 执行 MATLAB 表达式或多行语句，捕获 disp/fprintf 输出
   - 超时 60 秒，错误返回结构化信息含行号
2. `matlab_execute_script(script_path: str)` → `{stdout, errors, execution_time_ms}`
   - 运行磁盘上的 .m 脚本文件

### 变量操作
3. `matlab_get_variable(name: str)` → `{value, type, dimensions, base64_bytes?}`
   - 标量→JSON 数字/字符串，矩阵→嵌套列表，大变量（>100KB）→base64
4. `matlab_set_variable(name: str, value: any, type_hint?: str)` → `{ok, name}`
   - JSON 值转回 MATLAB 类型，type_hint 支持 "matrix"、"struct" 等
5. `matlab_list_variables()` → `[{name, type, size, bytes}]`
   - 调用 MATLAB `whos()` 列出工作区所有变量

### 图 表
6. `matlab_get_figure(figure_id?: int, format?: "png"|"svg")` → `{image_base64, width, height, format}`
   - 将当前或指定图窗渲染为内存中的图片

### Simulink
7. `matlab_simulink_list()` → `[{name, status, simulation_time?}]`
   - 列出已打开的 Simulink 模型
8. `matlab_simulink_run(model_name: str, stop_time?: float, params?: dict)` → `{ok, simulation_output?}`
   - 运行指定模型的仿真

### 工作区与路径
9. `matlab_path_manage(action: "add"|"remove"|"list", path?: str)` → `{result}`
   - 管理 MATLAB 搜索路径
10. `matlab_workspace_manage(action: "clear"|"save"|"load", file_path?: str)` → `{ok}`
    - 清空/保存/加载工作区

## 关键设计决策

### 懒加载单例 Engine
```python
class MatlabSession:
    def __init__(self):
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = matlab.engine.start_matlab()
        return self._engine

    def shutdown(self):
        if self._engine:
            self._engine.quit()
```
- 懒加载：收到第一条命令才启动 MATLAB，避免无用占用
- 单例：整个会话共享一个 Engine，工作区跨命令保持
- 清理：服务退出时调用 `shutdown()` 释放 MATLAB 进程

### 变量传递策略
- 标量直接转 JSON 数字/字符串
- 矩阵：numpy.ndarray → 嵌套列表 → JSON
- 大变量（>100KB）：base64 编码 + 返回元信息
- 写入方向：JSON 值通过 `matlab.double()` / cell / struct 转回 MATLAB 类型

### 图表导出
- 使用 `exportgraphics()` 或 `getframe()` → 内存缓冲区
- 不在磁盘生成临时文件
- 支持 PNG（默认）和 SVG

### 错误处理
- `matlab.engine.MatlabExecutionError` → 结构化错误，含行号
- Engine 崩溃 → 自动重启一次，再次失败则报错
- 每条命令 60 秒超时限制

### 配置（config.py）
```python
@dataclass
class Config:
    matlab_workspace_dir: str = "."
    execution_timeout_seconds: int = 60
    max_variable_size_kb: int = 1024
    figure_export_format: str = "png"
    figure_default_width: int = 800
    figure_default_height: int = 600
```

## 安全性

- 所有命令在用户本地执行，无网络传输
- 60 秒硬超时防止死循环
- 1MB 变量上限防止内存溢出或 JSON-RPC 通道阻塞
- 不对 MATLAB 命令做沙箱限制——本地 Tool 的标准 MCP 信任模型

## 测试策略

### 单元测试（无需 MATLAB）
- Mock `matlab.engine`，测试 Tool 逻辑、错误处理、边界情况
- 覆盖：全部 10 个 Tool、会话生命周期、配置校验

### 集成测试（需要 MATLAB）
- `@pytest.mark.integration` 标记，手动触发
- 覆盖：真实命令执行、变量读写往返、图表渲染、Simulink

### 协议测试
- 使用 MCP Inspector（`npx @modelcontextprotocol/inspector`）验证 JSON-RPC 合规性

## 依赖

```toml
# pyproject.toml
[project]
name = "mcp-matlab"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "mcp[cli]>=1.0.0",
    "numpy>=1.21",
]
```

`matlab.engine` 不是 PyPI 包，须从 MATLAB 安装目录手动安装：
```
# 将 R20XXx 替换为实际 MATLAB 版本，如 R2024a
cd "C:/Program Files/MATLAB/R20XXx/extern/engines/python"
python setup.py install
```

## Claude Code MCP 配置

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
