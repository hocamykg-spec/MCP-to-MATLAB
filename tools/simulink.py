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
