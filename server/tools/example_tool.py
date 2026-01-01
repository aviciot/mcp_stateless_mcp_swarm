"""
Example Tool - Echo
===================
Demonstrates proper tool implementation with correct return format
"""

from mcp_app import mcp


@mcp.tool()
async def echo(message: str, repeat: int = 1) -> str:
    """
    Echo a message back, optionally repeating it
    
    Args:
        message: The message to echo
        repeat: Number of times to repeat (default: 1)
    
    Returns:
        str: The echoed message
    """
    # Validate input
    if repeat < 1:
        repeat = 1
    if repeat > 10:
        repeat = 10
    
    # Build response
    result = "\n".join([message] * repeat)
    
    # Return string directly - FastMCP handles the response format
    return result
