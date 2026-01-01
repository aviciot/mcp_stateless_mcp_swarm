"""
Template MCP Server - Starlette Application
===========================================
MCP server with authentication middleware
"""

import os
import sys
import logging
import warnings

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
import uvicorn

from config import get_config

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

# ========================================
# IMPORT ALL MODULES FIRST
# ========================================
from utils.import_utils import import_submodules

# Import all tools, resources, and prompts BEFORE creating HTTP app
import_submodules('tools')
import_submodules('resources')
import_submodules('prompts')

logger.info("All modules imported successfully")

# NOW import mcp after tools are registered
from mcp_app import mcp

# ========================================
# STARTUP BANNER
# ========================================
logger.info("=" * 80)
logger.info("🚀 Template MCP Server - Starting Up")
logger.info("=" * 80)
logger.info(f"📦 Version: {config.get('server.version', '1.0.0')}")
logger.info(f"🌐 Port: {os.getenv('MCP_PORT', config.get('server.port', 8000))}")

# Authentication status
auth_enabled = config.is_authentication_enabled()
auth_icon = "✅" if auth_enabled else "❌"
logger.info(f"🔐 Authentication: {auth_icon} {'Enabled' if auth_enabled else 'Disabled'}")

logger.info("-" * 80)
logger.info("📡 MCP Server: Ready")
logger.info("=" * 80)

# ========================================
# BUILD ASGI APP
# ========================================
os.environ["PYTHONUNBUFFERED"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Get FastMCP HTTP app and create Starlette with its lifespan
mcp_http_app = mcp.http_app()
app = Starlette(lifespan=mcp_http_app.lifespan)


# ========================================
# AUTHENTICATION MIDDLEWARE
# ========================================
class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware - validates Bearer token"""
    
    async def dispatch(self, request, call_next):
        # Skip auth for health check and info endpoints
        if request.url.path in ["/healthz", "/health", "/version", "/_info"]:
            return await call_next(request)
        
        # Check if authentication is enabled
        if not config.is_authentication_enabled():
            logger.debug("Authentication disabled - allowing request")
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("Missing Authorization header")
            return JSONResponse(
                {"error": "Missing Authorization header"},
                status_code=401
            )
        
        # Validate Bearer token format
        if not auth_header.startswith("Bearer "):
            logger.warning("Invalid Authorization header format")
            return JSONResponse(
                {"error": "Invalid Authorization header format. Use: Bearer <token>"},
                status_code=401
            )
        
        # Extract and validate token
        token = auth_header[7:]  # Remove "Bearer " prefix
        expected_token = config.get_auth_token()
        
        if token != expected_token:
            logger.warning("Invalid authentication token")
            return JSONResponse(
                {"error": "Invalid authentication token"},
                status_code=403
            )
        
        # Token valid - proceed
        logger.debug("Authentication successful")
        return await call_next(request)


# Add authentication middleware if enabled
if config.is_authentication_enabled():
    app.add_middleware(AuthenticationMiddleware)
    logger.info("Authentication middleware enabled")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# SIMPLE ENDPOINTS
# ========================================

async def health_check(request):
    """Health check endpoint"""
    return PlainTextResponse("OK")


async def version_info(request):
    """Version information endpoint"""
    return JSONResponse({
        "name": config.get('mcp.name', 'template-mcp'),
        "version": config.get('server.version', '1.0.0'),
        "status": "running"
    })


# ========================================
# ROUTES
# ========================================
app.add_route("/healthz", health_check, methods=["GET"])
app.add_route("/health", health_check, methods=["GET"])
app.add_route("/version", version_info, methods=["GET"])

# ========================================
# MOUNT FASTMCP HTTP APP
# ========================================
# Mount FastMCP at root
app.mount("/", mcp_http_app)

logger.info("✅ FastMCP mounted at /")

# ========================================
# MAIN
# ========================================
if __name__ == "__main__":
    port = int(os.getenv('MCP_PORT', config.get('server.port', 8000)))
    host = config.get('server.host', '0.0.0.0')
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
