def mcp_tool_to_openai_tool(mcp_tool):
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.input_schema
        }
    }

