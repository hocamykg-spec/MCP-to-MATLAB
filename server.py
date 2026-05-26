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
