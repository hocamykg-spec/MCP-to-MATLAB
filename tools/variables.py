import base64
import sys

try:
    import numpy as np
except ImportError:
    np = None  # MATLAB Engine not available; numpy-dependent paths skipped in tests


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
        raise KeyError(f"Variable '{name}' not found in MATLAB workspace")

    if np is not None and isinstance(val, np.ndarray):
        est_bytes = val.nbytes
        if est_bytes > max_size_kb * 1024:
            return None, base64.b64encode(val.tobytes()).decode("utf-8")
        return val.tolist(), None

    if isinstance(val, list):
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
        except Exception:
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
        engine = session.engine
        try:
            if isinstance(value, list) and type_hint == "matrix":
                if np is not None:
                    engine.workspace[name] = np.array(value, dtype=float)
                else:
                    engine.workspace[name] = value
            elif isinstance(value, list):
                if np is not None:
                    engine.workspace[name] = np.array(value, dtype=float)
                else:
                    engine.workspace[name] = value
            else:
                engine.workspace[name] = value
            return {"ok": True, "name": name}
        except Exception:
            return {"ok": False, "name": name}

    @mcp.tool()
    def matlab_list_variables() -> list:
        """列出工作区所有变量，等价于 MATLAB whos()"""
        engine = session.engine
        try:
            raw = str(engine.eval("evalc('whos')"))
            variables = []
            lines = raw.strip().split("\n")
            for line in lines[3:]:
                parts = line.split()
                if len(parts) >= 4:
                    variables.append({
                        "name": parts[0],
                        "type": parts[-1],
                        "size": parts[1],
                        "bytes": int(parts[2]) if parts[2].isdigit() else 0,
                    })
            return variables
        except Exception:
            return []
