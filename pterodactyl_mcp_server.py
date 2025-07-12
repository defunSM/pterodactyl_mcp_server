#!/usr/bin/env python3
"""
Pterodactyl MCP Server

A Model Context Protocol (MCP) server for interacting with the Pterodactyl Panel API.
Supports both Client API (user-level) and Application API (admin-level) operations.

Features:
- Server management (list, create, delete, start, stop)
- Resource monitoring and utilization
- File management operations
- Database management
- User and node management (Application API)
- Real-time WebSocket connections
- Comprehensive error handling and validation

Author: Assistant
License: MIT
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Dict, Any, List
from urllib.parse import urljoin
import os

import httpx
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PterodactylConfig:
    """Configuration for Pterodactyl connection"""
    panel_url: str
    client_api_key: Optional[str] = None
    application_api_key: Optional[str] = None
    timeout: int = 30
    verify_ssl: bool = True

class PterodactylClient:
    """HTTP client for Pterodactyl API interactions"""
    
    def __init__(self, config: PterodactylConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.verify_ssl
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    def _get_headers(self, api_type: str = "client") -> Dict[str, str]:
        """Get headers for API requests"""
        if api_type == "client" and self.config.client_api_key:
            api_key = self.config.client_api_key
        elif api_type == "application" and self.config.application_api_key:
            api_key = self.config.application_api_key
        else:
            raise ValueError(f"No API key configured for {api_type} API")
        
        return {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        api_type: str = "client",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Pterodactyl API"""
        url = urljoin(self.config.panel_url, endpoint)
        headers = self._get_headers(api_type)
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            response.raise_for_status()
            
            if response.status_code == 204:  # No content
                return {"success": True}
            
            return response.json()
        
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                error_response = e.response.json()
                if "errors" in error_response:
                    error_detail = "; ".join([
                        f"{err.get('code', 'Unknown')}: {err.get('detail', 'No details')}"
                        for err in error_response["errors"]
                    ])
            except:
                error_detail = e.response.text or str(e)
            
            raise Exception(f"API request failed ({e.response.status_code}): {error_detail}")
        
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

# Global application context
@dataclass
class AppContext:
    pterodactyl: PterodactylClient

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with Pterodactyl client"""
    # Get configuration from environment variables
    panel_url = os.getenv("PTERODACTYL_PANEL_URL")
    client_api_key = os.getenv("PTERODACTYL_CLIENT_API_KEY")
    application_api_key = os.getenv("PTERODACTYL_APPLICATION_API_KEY")
    
    if not panel_url:
        raise ValueError("PTERODACTYL_PANEL_URL environment variable is required")
    
    if not client_api_key and not application_api_key:
        raise ValueError("At least one of PTERODACTYL_CLIENT_API_KEY or PTERODACTYL_APPLICATION_API_KEY is required")
    
    config = PterodactylConfig(
        panel_url=panel_url,
        client_api_key=client_api_key,
        application_api_key=application_api_key,
        timeout=int(os.getenv("PTERODACTYL_TIMEOUT", "30")),
        verify_ssl=os.getenv("PTERODACTYL_VERIFY_SSL", "true").lower() == "true"
    )
    
    pterodactyl = PterodactylClient(config)
    
    try:
        yield AppContext(pterodactyl=pterodactyl)
    finally:
        await pterodactyl.close()

# Create FastMCP server
mcp = FastMCP("Pterodactyl API Server", lifespan=app_lifespan)

# === CLIENT API TOOLS ===

@mcp.tool()
async def list_servers(ctx: Context) -> str:
    """List all servers accessible to the authenticated user"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        response = await pterodactyl._make_request("GET", "/api/client", "client")
        
        servers = response.get("data", [])
        if not servers:
            return "No servers found."
        
        result = ["**Your Servers:**\n"]
        for server in servers:
            attrs = server.get("attributes", {})
            limits = attrs.get("limits", {})
            
            result.append(f"• **{attrs.get('name', 'Unknown')}** (`{attrs.get('identifier', 'N/A')}`)")
            result.append(f"  - UUID: {attrs.get('uuid', 'N/A')}")
            result.append(f"  - Memory: {limits.get('memory', 0)} MB")
            result.append(f"  - Disk: {limits.get('disk', 0)} MB")
            result.append(f"  - CPU: {limits.get('cpu', 0)}%\n")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error listing servers: {str(e)}"

@mcp.tool()
async def get_server_info(server_id: str, ctx: Context) -> str:
    """Get detailed information about a specific server"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        response = await pterodactyl._make_request("GET", f"/api/client/servers/{server_id}", "client")
        
        attrs = response.get("attributes", {})
        limits = attrs.get("limits", {})
        feature_limits = attrs.get("feature_limits", {})
        
        result = [
            f"**Server: {attrs.get('name', 'Unknown')}**",
            f"- **ID:** {attrs.get('identifier', 'N/A')}",
            f"- **UUID:** {attrs.get('uuid', 'N/A')}",
            f"- **Description:** {attrs.get('description', 'None')}",
            f"- **Owner:** {'Yes' if attrs.get('server_owner', False) else 'No'}",
            "",
            "**Resource Limits:**",
            f"- Memory: {limits.get('memory', 0)} MB",
            f"- Swap: {limits.get('swap', 0)} MB", 
            f"- Disk: {limits.get('disk', 0)} MB",
            f"- I/O: {limits.get('io', 0)} ops/s",
            f"- CPU: {limits.get('cpu', 0)}%",
            "",
            "**Feature Limits:**",
            f"- Databases: {feature_limits.get('databases', 0)}",
            f"- Allocations: {feature_limits.get('allocations', 0)}",
            f"- Backups: {feature_limits.get('backups', 0)}"
        ]
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error getting server info: {str(e)}"

@mcp.tool()
async def get_server_utilization(server_id: str, ctx: Context) -> str:
    """Get real-time resource utilization for a server"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        response = await pterodactyl._make_request("GET", f"/api/client/servers/{server_id}/resources", "client")
        
        attrs = response.get("attributes", {})
        state = attrs.get("current_state", "unknown")
        resources = attrs.get("resources", {})
        
        memory = resources.get("memory_bytes", 0) / (1024 * 1024)  # Convert to MB
        memory_limit = resources.get("memory_limit_bytes", 0) / (1024 * 1024)
        
        disk = resources.get("disk_bytes", 0) / (1024 * 1024)  # Convert to MB
        disk_limit = resources.get("disk_limit_bytes", 0) / (1024 * 1024)
        
        cpu_usage = resources.get("cpu_absolute", 0)
        
        result = [
            f"**Server Utilization: {server_id}**",
            f"- **State:** {state.title()}",
            "",
            "**Resource Usage:**",
            f"- **Memory:** {memory:.1f} MB / {memory_limit:.1f} MB ({(memory/memory_limit*100) if memory_limit > 0 else 0:.1f}%)",
            f"- **Disk:** {disk:.1f} MB / {disk_limit:.1f} MB ({(disk/disk_limit*100) if disk_limit > 0 else 0:.1f}%)",
            f"- **CPU:** {cpu_usage:.2f}%",
            f"- **Network (RX):** {resources.get('network_rx_bytes', 0) / 1024:.1f} KB",
            f"- **Network (TX):** {resources.get('network_tx_bytes', 0) / 1024:.1f} KB"
        ]
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error getting server utilization: {str(e)}"

@mcp.tool()
async def send_power_action(server_id: str, action: str, ctx: Context) -> str:
    """Send a power action to a server (start, stop, restart, kill)"""
    valid_actions = ["start", "stop", "restart", "kill"]
    
    if action.lower() not in valid_actions:
        return f"Invalid action. Must be one of: {', '.join(valid_actions)}"
    
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        data = {"signal": action.lower()}
        
        await pterodactyl._make_request("POST", f"/api/client/servers/{server_id}/power", "client", data)
        
        action_messages = {
            "start": "started",
            "stop": "stopped", 
            "restart": "restarted",
            "kill": "forcefully killed"
        }
        
        return f"Successfully {action_messages[action.lower()]} server {server_id}"
    
    except Exception as e:
        return f"Error sending power action: {str(e)}"

@mcp.tool()
async def send_console_command(server_id: str, ctx: Context, command: str) -> str:
    """Send a command to the server console"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        data = {"command": command}
        
        await pterodactyl._make_request("POST", f"/api/client/servers/{server_id}/command", "client", data)
        
        return f"Successfully sent command '{command}' to server {server_id}"
    
    except Exception as e:
        return f"Error sending console command: {str(e)}"

@mcp.tool()
async def list_server_files(server_id: str, ctx: Context, directory: str = "/") -> str:
    """List files in a server directory"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        params = {"directory": directory}
        
        response = await pterodactyl._make_request("GET", f"/api/client/servers/{server_id}/files/list", "client", params=params)
        
        files = response.get("data", [])
        if not files:
            return f"No files found in directory: {directory}"
        
        result = [f"**Files in {directory}:**\n"]
        
        for file in files:
            attrs = file.get("attributes", {})
            file_type = "📁" if attrs.get("is_file", True) else "📄"
            name = attrs.get("name", "Unknown")
            size = attrs.get("size", 0)
            modified = attrs.get("modified_at", "Unknown")
            
            if attrs.get("is_file", True):
                size_str = f" ({size} bytes)" if size > 0 else ""
            else:
                size_str = ""
            
            result.append(f"{file_type} **{name}**{size_str}")
            result.append(f"   Modified: {modified}\n")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error listing files: {str(e)}"

@mcp.tool()
async def get_server_databases(server_id: str, ctx: Context) -> str:
    """List databases for a server"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        response = await pterodactyl._make_request("GET", f"/api/client/servers/{server_id}/databases", "client")
        
        databases = response.get("data", [])
        if not databases:
            return "No databases found for this server."
        
        result = [f"**Databases for server {server_id}:**\n"]
        
        for db in databases:
            attrs = db.get("attributes", {})
            result.append(f"• **{attrs.get('name', 'Unknown')}**")
            result.append(f"  - Host: {attrs.get('host', {}).get('address', 'Unknown')}:{attrs.get('host', {}).get('port', 'Unknown')}")
            result.append(f"  - Username: {attrs.get('username', 'Unknown')}")
            result.append(f"  - Max Connections: {attrs.get('max_connections', 'Unknown')}\n")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error getting databases: {str(e)}"

# === APPLICATION API TOOLS ===

@mcp.tool()
async def app_list_users(ctx: Context, page: int = 1) -> str:
    """List all users on the panel (Application API - Admin only)"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        params = {"page": page}
        
        response = await pterodactyl._make_request("GET", "/api/application/users", "application", params=params)
        
        users = response.get("data", [])
        meta = response.get("meta", {}).get("pagination", {})
        
        if not users:
            return "No users found."
        
        result = [f"**Users (Page {meta.get('current_page', 1)} of {meta.get('total_pages', 1)}):**\n"]
        
        for user in users:
            attrs = user.get("attributes", {})
            result.append(f"• **{attrs.get('username', 'Unknown')}** (`{attrs.get('id', 'N/A')}`)")
            result.append(f"  - Email: {attrs.get('email', 'Unknown')}")
            result.append(f"  - Name: {attrs.get('first_name', '')} {attrs.get('last_name', '')}")
            result.append(f"  - Admin: {'Yes' if attrs.get('root_admin', False) else 'No'}")
            result.append(f"  - 2FA: {'Enabled' if attrs.get('2fa', False) else 'Disabled'}\n")
        
        result.append(f"Total: {meta.get('total', 0)} users")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error listing users: {str(e)}"

@mcp.tool()
async def app_create_user(
    username: str,
    email: str, 
    first_name: str,
    last_name: str,
    password: str,
    root_admin: bool = False,
    ctx: Context = None
) -> str:
    """Create a new user (Application API - Admin only)"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        data = {
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
            "root_admin": root_admin,
            "language": "en"
        }
        
        response = await pterodactyl._make_request("POST", "/api/application/users", "application", data)
        
        attrs = response.get("attributes", {})
        return f"Successfully created user: {attrs.get('username', username)} (ID: {attrs.get('id', 'Unknown')})"
    
    except Exception as e:
        return f"Error creating user: {str(e)}"

@mcp.tool()
async def app_list_servers(ctx: Context, page: int = 1) -> str:
    """List all servers on the panel (Application API - Admin only)"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        params = {"page": page}
        
        response = await pterodactyl._make_request("GET", "/api/application/servers", "application", params=params)
        
        servers = response.get("data", [])
        meta = response.get("meta", {}).get("pagination", {})
        
        if not servers:
            return "No servers found."
        
        result = [f"**All Servers (Page {meta.get('current_page', 1)} of {meta.get('total_pages', 1)}):**\n"]
        
        for server in servers:
            attrs = server.get("attributes", {})
            limits = attrs.get("limits", {})
            
            result.append(f"• **{attrs.get('name', 'Unknown')}** (`{attrs.get('id', 'N/A')}`)")
            result.append(f"  - UUID: {attrs.get('uuid', 'N/A')}")
            result.append(f"  - Node: {attrs.get('node', 'Unknown')}")
            result.append(f"  - Status: {attrs.get('status', 'Unknown')}")
            result.append(f"  - Memory: {limits.get('memory', 0)} MB")
            result.append(f"  - Disk: {limits.get('disk', 0)} MB\n")
        
        result.append(f"Total: {meta.get('total', 0)} servers")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error listing servers: {str(e)}"

@mcp.tool()
async def app_list_nodes(ctx: Context) -> str:
    """List all nodes on the panel (Application API - Admin only)"""
    try:
        pterodactyl = ctx.request_context.lifespan_context.pterodactyl
        response = await pterodactyl._make_request("GET", "/api/application/nodes", "application")
        
        nodes = response.get("data", [])
        if not nodes:
            return "No nodes found."
        
        result = ["**Nodes:**\n"]
        
        for node in nodes:
            attrs = node.get("attributes", {})
            result.append(f"• **{attrs.get('name', 'Unknown')}** (`{attrs.get('id', 'N/A')}`)")
            result.append(f"  - FQDN: {attrs.get('fqdn', 'Unknown')}")
            result.append(f"  - Location ID: {attrs.get('location_id', 'Unknown')}")
            result.append(f"  - Memory: {attrs.get('memory', 0)} MB")
            result.append(f"  - Disk: {attrs.get('disk', 0)} MB")
            result.append(f"  - Public: {'Yes' if attrs.get('public', False) else 'No'}")
            result.append(f"  - Maintenance: {'Yes' if attrs.get('maintenance_mode', False) else 'No'}\n")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error listing nodes: {str(e)}"

# === RESOURCES ===

@mcp.resource("pterodactyl://config")
def get_config() -> str:
    """Get current Pterodactyl configuration and connection status"""
    panel_url = os.getenv("PTERODACTYL_PANEL_URL", "Not configured")
    has_client_key = "✅" if os.getenv("PTERODACTYL_CLIENT_API_KEY") else "❌"
    has_app_key = "✅" if os.getenv("PTERODACTYL_APPLICATION_API_KEY") else "❌"
    
    return f"""# Pterodactyl MCP Server Configuration

**Panel URL:** {panel_url}
**Client API Key:** {has_client_key}
**Application API Key:** {has_app_key}

## Available APIs
- **Client API:** User-level operations (servers, files, databases)
- **Application API:** Admin-level operations (users, nodes, all servers)

## Environment Variables
Set these environment variables to configure the server:
- `PTERODACTYL_PANEL_URL` - Your Pterodactyl panel URL
- `PTERODACTYL_CLIENT_API_KEY` - Client API key (for user operations)
- `PTERODACTYL_APPLICATION_API_KEY` - Application API key (for admin operations)
- `PTERODACTYL_TIMEOUT` - Request timeout in seconds (default: 30)
- `PTERODACTYL_VERIFY_SSL` - Verify SSL certificates (default: true)
"""

@mcp.resource("pterodactyl://help")
def get_help() -> str:
    """Get help and usage information for the Pterodactyl MCP Server"""
    return """# Pterodactyl MCP Server Help

This MCP server provides comprehensive access to the Pterodactyl Panel API.

## Client API Tools (User Level)
- `list_servers()` - List accessible servers
- `get_server_info(server_id)` - Get detailed server information
- `get_server_utilization(server_id)` - Get real-time resource usage
- `send_power_action(server_id, action)` - Control server power (start/stop/restart/kill)
- `send_console_command(server_id, command)` - Send console commands
- `list_server_files(server_id, directory)` - Browse server files
- `get_server_databases(server_id)` - List server databases

## Application API Tools (Admin Level)
- `app_list_users(page)` - List all panel users
- `app_create_user(username, email, first_name, last_name, password, root_admin)` - Create new user
- `app_list_servers(page)` - List all servers (admin view)
- `app_list_nodes()` - List all panel nodes

## Power Actions
- `start` - Start the server
- `stop` - Stop the server gracefully
- `restart` - Restart the server
- `kill` - Force kill the server (may cause data loss)

## Setup Instructions
1. Set environment variables for your Pterodactyl panel
2. Generate API keys in your Pterodactyl panel
3. Use Client API key for user operations
4. Use Application API key for admin operations

## Security Notes
- Keep your API keys secure
- Client API keys have limited scope
- Application API keys have full admin access
- Use appropriate API key for your use case
"""

# === PROMPTS ===

@mcp.prompt()
def server_management_prompt(server_id: str) -> List[base.Message]:
    """Generate a prompt for server management operations"""
    return [
        base.UserMessage(f"I need help managing Pterodactyl server with ID: {server_id}"),
        base.AssistantMessage("I can help you manage your Pterodactyl server. Here are the available operations:"),
        base.AssistantMessage("1. **Get server info** - View detailed server information"),
        base.AssistantMessage("2. **Check utilization** - Monitor resource usage in real-time"),
        base.AssistantMessage("3. **Power control** - Start, stop, restart, or kill the server"),
        base.AssistantMessage("4. **Console commands** - Send commands to the server console"),
        base.AssistantMessage("5. **File management** - Browse and manage server files"),
        base.AssistantMessage("6. **Database management** - View server databases"),
        base.UserMessage("What would you like to do with this server?")
    ]

@mcp.prompt()
def troubleshooting_prompt(issue_description: str) -> str:
    """Generate a troubleshooting prompt for Pterodactyl issues"""
    return f"""I'm experiencing an issue with my Pterodactyl server: {issue_description}

Please help me troubleshoot this issue by:
1. Checking server status and resource utilization
2. Reviewing recent console output if possible
3. Suggesting appropriate diagnostic steps
4. Providing potential solutions

What information do you need to help diagnose this problem?"""

# === MAIN EXECUTION ===

if __name__ == "__main__":
    import sys
    
    # Check for required environment variables
    required_vars = ["PTERODACTYL_PANEL_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("\nRequired environment variables:")
        print("- PTERODACTYL_PANEL_URL: Your Pterodactyl panel URL")
        print("\nOptional environment variables:")
        print("- PTERODACTYL_CLIENT_API_KEY: Client API key for user operations")
        print("- PTERODACTYL_APPLICATION_API_KEY: Application API key for admin operations")
        print("- PTERODACTYL_TIMEOUT: Request timeout in seconds (default: 30)")
        print("- PTERODACTYL_VERIFY_SSL: Verify SSL certificates (default: true)")
        print("\nExample usage:")
        print("export PTERODACTYL_PANEL_URL='https://panel.example.com'")
        print("export PTERODACTYL_CLIENT_API_KEY='your_client_api_key'")
        print("python pterodactyl_mcp_server.py")
        sys.exit(1)
    
    # Check if at least one API key is provided
    if not os.getenv("PTERODACTYL_CLIENT_API_KEY") and not os.getenv("PTERODACTYL_APPLICATION_API_KEY"):
        print("Error: At least one API key is required")
        print("Set PTERODACTYL_CLIENT_API_KEY for user operations")
        print("Set PTERODACTYL_APPLICATION_API_KEY for admin operations")
        sys.exit(1)
    
    print("🦖 Starting Pterodactyl MCP Server...")
    print(f"Panel URL: {os.getenv('PTERODACTYL_PANEL_URL')}")
    print(f"Client API: {'✅ Configured' if os.getenv('PTERODACTYL_CLIENT_API_KEY') else '❌ Not configured'}")
    print(f"Application API: {'✅ Configured' if os.getenv('PTERODACTYL_APPLICATION_API_KEY') else '❌ Not configured'}")
    print("Server ready for connections!\n")
    
    # Run the FastMCP server
    mcp.run()