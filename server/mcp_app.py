"""
Template MCP Application - FastMCP Instance
===========================================
Main MCP server using FastMCP framework

IMPORTANT: This uses STATELESS MODE for horizontal scaling!
- stateless_http=True: No session tracking, any replica handles any request
- json_response=True: JSON responses instead of SSE streams

Trade-offs:
- ✅ True horizontal scaling (round-robin load balancing)
- ✅ Works with Swarm/K8s replicas
- ❌ No server-to-client push notifications
- ❌ No real-time progress updates (must poll)
"""

import os
import logging
from fastmcp import FastMCP

from config import get_config

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

# Check if stateless mode is enabled (default: True for scaling)
STATELESS_MODE = os.getenv("STATELESS_HTTP", "true").lower() in ("1", "true", "yes", "on")

# Create FastMCP instance with stateless mode for horizontal scaling
mcp = FastMCP(
    name=config.get('mcp.name', 'template-mcp'),
    stateless_http=STATELESS_MODE,  # KEY: Enables multi-replica scaling
    json_response=True               # JSON instead of SSE (recommended for stateless)
)

mode_str = "STATELESS (scalable)" if STATELESS_MODE else "STATEFUL (single replica)"
logger.info(f"Initializing {mcp.name} in {mode_str} mode")
