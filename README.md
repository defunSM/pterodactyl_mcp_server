# Pterodactyl MCP Server 🦖

A comprehensive Model Context Protocol (MCP) server for the [Pterodactyl Panel](https://pterodactyl.io/) API, built with Python and Context7 integration.

## Features

- **Complete API Coverage**: Supports both Client API (user-level) and Application API (admin-level) operations
- **Server Management**: List, monitor, start, stop, restart servers
- **Real-time Monitoring**: Get server resource utilization and status
- **File Operations**: Browse and manage server files
- **Database Management**: View and manage server databases
- **User Administration**: Create and manage panel users (admin only)
- **Node Management**: Monitor and manage panel nodes (admin only)
- **Console Commands**: Send commands to server consoles
- **Error Handling**: Comprehensive error handling and validation
- **Secure**: Proper API key management and SSL verification

## Quick Start

### 1. Installation

```bash
# Clone or download the server files
# Install dependencies
pip install -r requirements.txt

# OR install directly with uv
uv add "mcp[cli]" httpx python-dotenv
```

### 2. Get API Keys

#### Client API Key (for user operations)
1. Log into your Pterodactyl panel
2. Go to **Account Settings** → **API Credentials**
3. Click **Create New**
4. Set description and allowed IPs (optional)
5. Copy the generated key

#### Application API Key (for admin operations)
1. Log into Pterodactyl as an administrator
2. Go to **Admin Area** → **Application API**
3. Click **Create New**
4. Select all necessary permissions
5. Copy the generated key

### 3. Configuration

Set environment variables:

```bash
export PTERODACTYL_PANEL_URL="https://your-panel.example.com"
export PTERODACTYL_CLIENT_API_KEY="your_client_api_key_here"
export PTERODACTYL_APPLICATION_API_KEY="your_application_api_key_here"  # Optional, for admin features

# Optional settings
export PTERODACTYL_TIMEOUT="30"
export PTERODACTYL_VERIFY_SSL="true"
```

Or create a `.env` file:

```env
PTERODACTYL_PANEL_URL=https://your-panel.example.com
PTERODACTYL_CLIENT_API_KEY=your_client_api_key_here
PTERODACTYL_APPLICATION_API_KEY=your_application_api_key_here
PTERODACTYL_TIMEOUT=30
PTERODACTYL_VERIFY_SSL=true
```

### 4. Run the Server

```bash
# Direct execution
python pterodactyl_mcp_server.py

# With MCP CLI
mcp dev pterodactyl_mcp_server.py

# Install for Claude Desktop
mcp install pterodactyl_mcp_server.py --name "Pterodactyl Panel"
```

## Available Tools

### Client API Tools (User Level)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_servers()` | List all accessible servers | None |
| `get_server_info(server_id)` | Get detailed server information | server_id |
| `get_server_utilization(server_id)` | Get real-time resource usage | server_id |
| `send_power_action(server_id, action)` | Control server power | server_id, action (start/stop/restart/kill) |
| `send_console_command(server_id, command)` | Send console commands | server_id, command |
| `list_server_files(server_id, directory)` | Browse server files | server_id, directory (default: "/") |
| `get_server_databases(server_id)` | List server databases | server_id |

### Application API Tools (Admin Level)

| Tool | Description | Parameters |
|------|-------------|------------|
| `app_list_users(page)` | List all panel users | page (default: 1) |
| `app_create_user(...)` | Create a new user | username, email, first_name, last_name, password, root_admin |
| `app_list_servers(page)` | List all servers (admin view) | page (default: 1) |
| `app_list_nodes()` | List all panel nodes | None |

## Available Resources

- `pterodactyl://config` - View current configuration and connection status
- `pterodactyl://help` - Get comprehensive help and usage information

## Available Prompts

- `server_management_prompt(server_id)` - Interactive server management assistant
- `troubleshooting_prompt(issue_description)` - Server troubleshooting guide

## Usage Examples

### Basic Server Management

```python
# List your servers
await list_servers()

# Get specific server info
await get_server_info("d3aac109")

# Check server resource usage
await get_server_utilization("d3aac109")

# Start a server
await send_power_action("d3aac109", "start")

# Send a console command
await send_console_command("d3aac109", "say Hello World!")
```

### File Management

```python
# List files in root directory
await list_server_files("d3aac109", "/")

# List files in a specific directory
await list_server_files("d3aac109", "/plugins")
```

### Administrative Tasks

```python
# List all users (admin only)
await app_list_users()

# Create a new user (admin only)
await app_create_user(
    username="newuser",
    email="user@example.com",
    first_name="John",
    last_name="Doe",
    password="secure_password",
    root_admin=False
)

# List all servers from admin perspective
await app_list_servers()

# List all nodes
await app_list_nodes()
```

## Integration with Claude Desktop

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pterodactyl": {
      "command": "python",
      "args": ["/path/to/pterodactyl_mcp_server.py"],
      "env": {
        "PTERODACTYL_PANEL_URL": "https://your-panel.example.com",
        "PTERODACTYL_CLIENT_API_KEY": "your_client_api_key_here",
        "PTERODACTYL_APPLICATION_API_KEY": "your_application_api_key_here"
      }
    }
  }
}
```

## Context7 Integration

This server is designed to work seamlessly with Context7. When asking questions about Pterodactyl management, append `use context7` to get the latest Pterodactyl documentation:

```
How do I configure a Minecraft server in Pterodactyl? use context7
```

## Security Considerations

- **API Key Security**: Store API keys securely and never commit them to version control
- **Principle of Least Privilege**: Use Client API keys for user operations, Application API keys only for admin tasks
- **SSL Verification**: Keep `PTERODACTYL_VERIFY_SSL=true` in production
- **Rate Limiting**: The Pterodactyl API has rate limits (60 requests/minute)
- **Power Actions**: Use `kill` action sparingly as it may cause data corruption

## Error Handling

The server includes comprehensive error handling:

- **API Errors**: Detailed error messages from Pterodactyl API
- **Network Issues**: Timeout and connection error handling  
- **Authentication**: Clear messages for invalid API keys
- **Validation**: Input validation for all parameters
- **Rate Limiting**: Automatic handling of rate limit responses

## Development

### Running in Development

```bash
# With hot reload
mcp dev pterodactyl_mcp_server.py

# With dependencies
mcp dev pterodactyl_mcp_server.py --with httpx --with python-dotenv

# Test with MCP Inspector
mcp dev pterodactyl_mcp_server.py
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PTERODACTYL_PANEL_URL` | ✅ | - | Your Pterodactyl panel URL |
| `PTERODACTYL_CLIENT_API_KEY` | ⚠️ | - | Client API key (required for user operations) |
| `PTERODACTYL_APPLICATION_API_KEY` | ⚠️ | - | Application API key (required for admin operations) |
| `PTERODACTYL_TIMEOUT` | ❌ | 30 | Request timeout in seconds |
| `PTERODACTYL_VERIFY_SSL` | ❌ | true | Verify SSL certificates |

⚠️ At least one API key is required

## Troubleshooting

### Common Issues

1. **"No API key configured"**
   - Ensure you've set the appropriate environment variables
   - Check that the API key is valid and hasn't expired

2. **"SSL verification failed"**
   - Set `PTERODACTYL_VERIFY_SSL=false` for self-signed certificates
   - Or properly configure SSL certificates

3. **"Rate limit exceeded"**
   - The API has a 60 requests/minute limit
   - Wait before making more requests

4. **"Server not found"**
   - Check that the server ID is correct
   - Ensure you have access to the server

### Debug Mode

Run with debug logging:

```bash
export PYTHONPATH=$PYTHONPATH:.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('pterodactyl_mcp_server.py').read())
"
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

- **Issues**: Open an issue on GitHub
- **Documentation**: Check the [Pterodactyl API docs](https://dashflo.net/docs/api/pterodactyl/v1/)
- **MCP Documentation**: Visit the [Model Context Protocol docs](https://modelcontextprotocol.io/)

## Acknowledgments

- [Pterodactyl Panel](https://pterodactyl.io/) - The amazing game server management panel
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol that makes this possible
- [Context7](https://context7.com/) - For up-to-date documentation integration
- [FastMCP](https://github.com/cris-0k/mcp-server-python-template) - The Python MCP framework

---

Made with ❤️ for the Pterodactyl community