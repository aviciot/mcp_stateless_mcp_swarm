"""
Template MCP Application - FastMCP Instance
===========================================
Main MCP server using FastMCP framework
"""

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

# Create FastMCP instance
mcp = FastMCP(
    name=config.get('mcp.name', 'template-mcp')
)

logger.info(f"Initializing {mcp.name}")

# ========================================
# AUTO-IMPORT AND REGISTER TOOLS
# ========================================
# Import all tools, resources, and prompts
# This ensures they are registered with @mcp.tool() decorators before server starts
from utils.import_utils import import_submodules

import_submodules('tools')
import_submodules('resources')
import_submodules('prompts')

logger.info("All tools, resources, and prompts registered")
