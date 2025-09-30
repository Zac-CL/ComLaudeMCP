# ComLaudeMCP

A Model Context Protocol (MCP) server that provides access to Com Laude's domain management, SSL certificate, and account services through their REST API.

## Overview

This MCP server acts as a bridge between MCP-compatible clients (like Claude Desktop) and the Com Laude API, allowing you to:

- Manage domain registrations and DNS settings
- Monitor and manage SSL certificates
- Access account information and settings
- Search and filter accounts
- Manage contacts and services

## Features

### Available Tools

The server provides the following tools:

- **Account Management**
  - `get_accounts` - List accounts for a group
  - `get_account` - Get details for a specific account
  - `update_account` - Update account information
  - `search_accounts` - Search accounts with filters

- **Domain Management**
  - `get_domains` - List domains
  - `get_domain` - Get details for a specific domain

- **SSL Certificate Management**
  - `get_ssl_certificates` - List SSL certificates

- **Contact Management**
  - `get_contacts` - List contacts

- **Service Management**
  - `get_services` - Get available services

- **Configuration**
  - `configure_api` - Configure API client settings

### Available Resources

The server exposes these resources:
- `comlaude://accounts` - Account management
- `comlaude://domains` - Domain management and DNS
- `comlaude://ssl-certificates` - SSL certificate management
- `comlaude://contacts` - Contact management
- `comlaude://services` - Available services

## Prerequisites

- Docker and Docker Compose
- Com Laude API key (Bearer token)
- Group ID from your Com Laude account

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ComLaudeMCP
```

### 2. Configure Environment

Copy the example environment file and add your API credentials:

```bash
cp env.example .env
```

Edit `.env` and add your Com Laude API key:

```bash
# Your Com Laude API Bearer token
COMLAUDE_API_KEY=your_actual_api_key_here

# Com Laude API base URL (usually doesn't need to be changed)
COMLAUDE_BASE_URL=https://api.comlaude.com
```

### 3. Start the Server

Use the provided startup script:

```bash
chmod +x start.sh
./start.sh
```

Or start manually with Docker Compose:

```bash
docker compose up --build -d
```

### 4. Verify Installation

Test the server setup:

```bash
python test_server.py
```

## Usage

### Connecting to MCP Clients

This server communicates via stdio (standard input/output) following the MCP protocol. Configure your MCP client to connect to this server.

### Example Usage

Once connected, you can use the tools through your MCP client. For example:

1. **Configure the API** (first step):
   ```json
   {
     "tool": "configure_api",
     "arguments": {
       "api_key": "your_api_key_here",
       "base_url": "https://api.comlaude.com",
       "timeout": 30,
       "max_retries": 2,
       "backoff_factor": 0.5
     }
   }
   ```

2. **Get accounts**:
   ```json
   {
     "tool": "get_accounts",
     "arguments": {
       "group_id": "your_group_id",
       "limit": 50,
       "page": 1
     }
   }
   ```

3. **Search accounts**:
   ```json
   {
     "tool": "search_accounts",
     "arguments": {
       "group_id": "your_group_id",
       "filters": {
         "status": "active",
         "type": "premium"
       },
       "limit": 25,
       "sort": "name"
     }
   }
   ```

## Development

### Running Locally (without Docker)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export COMLAUDE_API_KEY="your_api_key_here"
   export COMLAUDE_BASE_URL="https://api.comlaude.com"
   ```

3. Run the server:
   ```bash
   python mcp_server.py
   ```

### Project Structure

```
ComLaudeMCP/
├── mcp_server.py           # Main MCP server implementation
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker container definition
├── requirements.txt        # Python dependencies
├── env.example             # Environment variables template
├── start.sh                # Startup script
├── test_server.py          # Test script
└── README.md               # This file
```

### Key Components

- **ComLaudeAPIClient**: Handles HTTP requests to the Com Laude API
- **MCP Server**: Implements the Model Context Protocol interface
- **Tool Handlers**: Process tool calls and return results
- **Resource Handlers**: Manage available resources

## Configuration

### Environment Variables

- `COMLAUDE_API_KEY` - Your Com Laude API Bearer token (required)
- `COMLAUDE_BASE_URL` - API base URL (default: https://api.comlaude.com)

### Docker Configuration

The Docker setup includes:
- Health checks
- Resource limits (512MB memory, 0.5 CPU)
- Log volume mounting
- Non-root user for security

### Troubleshooting

### Common Issues

1. **API Key Issues**
   - Ensure your API key is valid and has proper permissions
   - Check that the key is correctly set in the `.env` file

2. **Group ID Issues**
   - Verify you're using the correct Group ID from your Com Laude account
   - Group ID is required for most operations

3. **Docker Issues**
   - Ensure Docker is running: `docker info`
   - Check container logs: `docker compose logs comlaude-mcp-server`
   - Verify container health: `docker compose ps`

4. **Connection Issues**
   - Test the server: `python test_server.py`
   - Check network connectivity to `https://api.comlaude.com`

### Logs

View server logs:
```bash
docker compose logs -f comlaude-mcp-server
```

## API Reference

### Com Laude API Endpoints

The server interacts with these Com Laude API endpoints:

- `GET /groups/{group_id}/accounts` - List accounts
- `GET /groups/{group_id}/accounts/{account_id}` - Get account details
- `PATCH /groups/{group_id}/accounts/{account_id}` - Update account
- `POST /groups/{group_id}/accounts/search` - Search accounts
- `GET /groups/{group_id}/domains` - List domains
- `GET /groups/{group_id}/domains/{domain_id}` - Get domain details
- `GET /groups/{group_id}/ssl-certificates` - List SSL certificates
- `GET /groups/{group_id}/contacts` - List contacts
- `GET /groups/{group_id}/accounts/services` - Get services

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues related to:
- **This MCP Server**: Create an issue in this repository
- **Com Laude API**: Contact Com Laude support
- **MCP Protocol**: Refer to the [MCP documentation](https://modelcontextprotocol.io/)