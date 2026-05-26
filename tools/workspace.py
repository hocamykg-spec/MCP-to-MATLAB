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
