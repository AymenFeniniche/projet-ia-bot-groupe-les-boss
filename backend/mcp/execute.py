from mcp.registry import TOOLS

def execute_tool(tool_name: str, args: dict) -> dict:
    if tool_name not in TOOLS:
        return {"result": None, "error": {"code": "UNKNOWN_TOOL", "message": tool_name}}

    handler = TOOLS[tool_name]["handler"]
    try:
        result = handler(args)
        return {"result": result, "error": None}
    except Exception as e:
        return {"result": None, "error": {"code": "TOOL_FAILED", "message": str(e)}}