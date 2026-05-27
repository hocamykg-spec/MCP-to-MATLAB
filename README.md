# MCP-MATLAB

基于MATLAB Engine API的MCP（模型上下文协议）服务器，用于MATLAB集成。

该服务器使LLM能够与MATLAB交互，执行命令、管理变量、导出图形、控制Simulink模型以及管理工作区。

## 功能特性

- **命令执行**：执行MATLAB表达式和脚本
- **变量管理**：读取、写入和列出工作区变量
- **图形导出**：将MATLAB图形导出为PNG或SVG图像
- **Simulink控制**：列出和运行Simulink模型仿真
- **工作区管理**：管理MATLAB搜索路径和工作区变量

## 前提条件

1. **MATLAB安装**：必须安装MATLAB R2024b或更高版本
2. **MATLAB Engine API**：必须安装Python版MATLAB Engine API
3. **Python 3.9+**：需要Python 3.9或更高版本

## 安装指南

### 1. 安装MATLAB Engine API

首先，安装Python版MATLAB Engine API：

```bash
# 导航到MATLAB安装目录
cd "C:\Program Files\MATLAB\R2024b\extern\engines\python"

# 安装MATLAB Engine API
python setup.py install
```

### 2. 安装MCP-MATLAB

```bash
# 克隆仓库
git clone https://github.com/your-username/mcp-matlab.git
cd mcp-matlab

# 安装依赖
pip install -e .
```

### 3. 验证安装

测试MATLAB连接：

```bash
python -c "import matlab.engine; print('MATLAB Engine API安装成功')"
```

## 配置说明

### 环境变量

设置以下环境变量（可选）：

```bash
# MATLAB安装路径（默认：D:\MATLAB）
set MATLAB_ROOT=C:\Program Files\MATLAB\R2024b

# MATLAB工作区目录（默认：当前目录）
set MATLAB_WORKSPACE_DIR=C:\Users\your-username\Documents\MATLAB
```

### 配置文件

编辑`config.py`来自定义设置：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    matlab_workspace_dir: str = "."  # MATLAB工作区目录
    execution_timeout_seconds: int = 60  # 命令执行超时时间
    max_variable_size_kb: int = 1024  # JSON传输的最大变量大小
    figure_export_format: str = "png"  # 默认图形导出格式
    figure_default_width: int = 800  # 默认图形宽度
    figure_default_height: int = 600  # 默认图形高度

DEFAULT_CONFIG = Config()
```

## 使用方法

### 启动服务器

```bash
# 启动MCP服务器
python server.py
```

服务器将启动并通过stdio传输监听MCP客户端连接。

### MCP客户端配置

将以下内容添加到MCP客户端配置中（例如Claude Desktop、Continue等）：

```json
{
  "mcpServers": {
    "matlab": {
      "command": "python",
      "args": ["path/to/mcp-matlab/server.py"],
      "env": {
        "MATLAB_ROOT": "C:\\Program Files\\MATLAB\\R2024b"
      }
    }
  }
}
```

## 可用工具

### 1. matlab_execute

执行MATLAB表达式或多行语句。

**参数：**
- `command`（字符串，必需）：要执行的MATLAB表达式或语句

**示例：**
```json
{
  "command": "x = 1:10; y = x.^2; plot(x, y);"
}
```

**响应：**
```json
{
  "stdout": "",
  "warnings": [],
  "errors": [],
  "execution_time_ms": 123.45
}
```

### 2. matlab_execute_script

从磁盘执行MATLAB .m脚本文件。

**参数：**
- `script_path`（字符串，必需）：.m脚本文件的绝对路径

**示例：**
```json
{
  "script_path": "C:/scripts/my_analysis.m"
}
```

### 3. matlab_get_variable

从MATLAB工作区读取变量。

**参数：**
- `name`（字符串，必需）：要检索的MATLAB变量名称

**示例：**
```json
{
  "name": "x"
}
```

**响应：**
```json
{
  "name": "x",
  "value": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "type": "double",
  "dimensions": "[1 10]",
  "base64_bytes": null
}
```

### 4. matlab_set_variable

将Python/JSON值写入MATLAB工作区。

**参数：**
- `name`（字符串，必需）：MATLAB变量名称
- `value`（必需）：要赋的值（标量或列表）
- `type_hint`（字符串，可选）：转换类型提示（'auto'、'scalar'、'matrix'、'string'）

**示例：**
```json
{
  "name": "A",
  "value": [[1, 2], [3, 4]],
  "type_hint": "matrix"
}
```

### 5. matlab_list_variables

列出MATLAB工作区中的所有变量。

**示例：**
```json
{}
```

**响应：**
```json
[
  {"name": "x", "type": "double", "size": "1x10", "bytes": 80},
  {"name": "A", "type": "double", "size": "2x2", "bytes": 32}
]
```

### 6. matlab_get_figure

将MATLAB图形导出为base64编码的图像。

**参数：**
- `figure_id`（整数，可选）：MATLAB图形ID（0表示当前图形）
- `format`（字符串，可选）：导出格式（'png'或'svg'）

**示例：**
```json
{
  "figure_id": 0,
  "format": "png"
}
```

### 7. matlab_simulink_list

列出所有当前打开的Simulink模型。

**示例：**
```json
{}
```

### 8. matlab_simulink_run

运行Simulink模型仿真。

**参数：**
- `model_name`（字符串，必需）：Simulink模型名称
- `stop_time`（浮点数，可选）：仿真停止时间（秒）
- `params`（对象，可选）：要设置的模型参数

**示例：**
```json
{
  "model_name": "my_model",
  "stop_time": 10.0,
  "params": {"Gain": "2"}
}
```

### 9. matlab_path_manage

管理MATLAB搜索路径。

**参数：**
- `action`（字符串，必需）：要执行的操作（'add'、'remove'或'list'）
- `path`（字符串，可选）：用于添加/删除操作的目录路径

**示例：**
```json
{
  "action": "add",
  "path": "C:/my_functions"
}
```

### 10. matlab_workspace_manage

管理工作区变量。

**参数：**
- `action`（字符串，必需）：要执行的操作（'clear'、'save'或'load'）
- `file_path`（字符串，可选）：用于保存/加载操作的文件路径

**示例：**
```json
{
  "action": "save",
  "file_path": "C:/data/workspace.mat"
}
```

## 测试

运行测试套件：

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v
```

## 故障排除

### 找不到MATLAB Engine

如果收到找不到MATLAB Engine的错误：

1. 确保已安装MATLAB且路径正确
2. 设置`MATLAB_ROOT`环境变量
3. 重新安装MATLAB Engine API

### 权限错误

如果遇到权限错误：

1. 以管理员身份运行命令提示符
2. 确保对MATLAB工作区目录具有写入权限

### 超时错误

如果命令超时：

1. 增加`config.py`中的`execution_timeout_seconds`
2. 检查MATLAB是否响应（尝试直接运行MATLAB）

## API密钥安全

**重要提示**：此MCP服务器不需要或存储任何API密钥。它通过MATLAB Engine API直接连接到本地MATLAB安装。不会进行外部API调用，也不会通过网络传输任何凭据。

## 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。

## 贡献指南

1. Fork本仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 创建Pull Request

## 支持

如需支持，请在GitHub仓库中创建issue或联系维护者。

## 更新日志

### 版本 1.0.0
- 初始发布
- MATLAB命令执行
- 变量管理
- 图形导出
- Simulink控制
- 工作区管理