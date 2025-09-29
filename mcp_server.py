#!/usr/bin/env python3
"""
MCP Server for Com Laude API
Provides access to Com Laude's domain management, SSL, and account services
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    Resource,
    TextContent,
    Tool,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComLaudeAPIClient:
    """Client for Com Laude API operations"""
    
    def __init__(self, base_url: str = "https://api.comlaude.com", api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make HTTP request to Com Laude API"""
        url = urljoin(self.base_url, endpoint)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=data
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                raise

# Global API client instance
api_client = ComLaudeAPIClient()

# Initialize MCP server
server = Server("comlaude-api")

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available Com Laude API resources"""
    return [
        Resource(
            uri="comlaude://accounts",
            name="Accounts",
            description="Com Laude account management",
            mimeType="application/json"
        ),
        Resource(
            uri="comlaude://domains",
            name="Domains",
            description="Domain management and DNS",
            mimeType="application/json"
        ),
        Resource(
            uri="comlaude://ssl-certificates",
            name="SSL Certificates",
            description="SSL certificate management",
            mimeType="application/json"
        ),
        Resource(
            uri="comlaude://contacts",
            name="Contacts",
            description="Contact management",
            mimeType="application/json"
        ),
        Resource(
            uri="comlaude://services",
            name="Services",
            description="Available services",
            mimeType="application/json"
        )
    ]

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available Com Laude API tools"""
    return [
        Tool(
            name="get_accounts",
            description="Get list of accounts for a group",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID to get accounts for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number",
                        "default": 1
                    }
                },
                "required": ["group_id"]
            }
        ),
        Tool(
            name="get_account",
            description="Get details for a specific account",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Account ID"
                    }
                },
                "required": ["group_id", "account_id"]
            }
        ),
        Tool(
            name="update_account",
            description="Update account information",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Account ID"
                    },
                    "updates": {
                        "type": "object",
                        "description": "Account fields to update"
                    }
                },
                "required": ["group_id", "account_id", "updates"]
            }
        ),
        Tool(
            name="search_accounts",
            description="Search accounts with filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Search filters to be sent in request body"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number",
                        "default": 1
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort field (with - prefix for descending)"
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return"
                    }
                },
                "required": ["group_id"]
            }
        ),
        Tool(
            name="get_domains",
            description="Get list of domains",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number",
                        "default": 1
                    }
                },
                "required": ["group_id"]
            }
        ),
        Tool(
            name="get_domain",
            description="Get details for a specific domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    },
                    "domain_id": {
                        "type": "string",
                        "description": "Domain ID"
                    }
                },
                "required": ["group_id", "domain_id"]
            }
        ),
        Tool(
            name="get_ssl_certificates",
            description="Get list of SSL certificates",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50
                    }
                },
                "required": ["group_id"]
            }
        ),
        Tool(
            name="get_contacts",
            description="Get list of contacts",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number",
                        "default": 1
                    }
                },
                "required": ["group_id"]
            }
        ),
        Tool(
            name="get_services",
            description="Get available services",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID"
                    }
                },
                "required": ["group_id"]
            }
        ),
        Tool(
            name="configure_api",
            description="Configure API client settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "Com Laude API key"
                    },
                    "base_url": {
                        "type": "string",
                        "description": "API base URL",
                        "default": "https://api.comlaude.com"
                    }
                },
                "required": ["api_key"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "configure_api":
            global api_client
            api_key = arguments.get("api_key")
            base_url = arguments.get("base_url", "https://api.comlaude.com")
            api_client = ComLaudeAPIClient(base_url=base_url, api_key=api_key)
            return [TextContent(
                type="text",
                text=f"API client configured with base URL: {base_url}"
            )]
        
        elif name == "get_accounts":
            group_id = arguments["group_id"]
            limit = arguments.get("limit", 50)
            page = arguments.get("page", 1)
            
            params = {
                "limit": limit,
                "page": page
            }
            
            result = await api_client.make_request(
                "GET",
                f"/groups/{group_id}/accounts",
                params=params
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_account":
            group_id = arguments["group_id"]
            account_id = arguments["account_id"]
            
            result = await api_client.make_request(
                "GET",
                f"/groups/{group_id}/accounts/{account_id}"
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "update_account":
            group_id = arguments["group_id"]
            account_id = arguments["account_id"]
            updates = arguments["updates"]
            
            result = await api_client.make_request(
                "PATCH",
                f"/groups/{group_id}/accounts/{account_id}",
                data=updates
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "search_accounts":
            group_id = arguments["group_id"]
            filters = arguments.get("filters", {})
            limit = arguments.get("limit", 50)
            page = arguments.get("page", 1)
            sort = arguments.get("sort", "")
            fields = arguments.get("fields", "")
            
            # Pagination and sorting parameters go in query params
            params = {
                "limit": limit,
                "page": page
            }
            if sort:
                params["sort"] = sort
            if fields:
                params["fields"] = fields
            
            # Filters go in the request body
            result = await api_client.make_request(
                "POST",
                f"/groups/{group_id}/accounts/search",
                params=params,
                data=filters
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_domains":
            group_id = arguments["group_id"]
            limit = arguments.get("limit", 50)
            page = arguments.get("page", 1)
            
            params = {
                "limit": limit,
                "page": page
            }
            
            result = await api_client.make_request(
                "GET",
                f"/groups/{group_id}/domains",
                params=params
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_domain":
            group_id = arguments["group_id"]
            domain_id = arguments["domain_id"]
            
            result = await api_client.make_request(
                "GET",
                f"/groups/{group_id}/domains/{domain_id}"
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_ssl_certificates":
            group_id = arguments["group_id"]
            limit = arguments.get("limit", 50)
            
            params = {"limit": limit}
            
            result = await api_client.make_request(
                "GET",
                f"/groups/{group_id}/ssl-certificates",
                params=params
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_contacts":
            group_id = arguments["group_id"]
            limit = arguments.get("limit", 50)
            page = arguments.get("page", 1)
            
            params = {
                "limit": limit,
                "page": page
            }
            
            result = await api_client.make_request(
                "GET",
                f"/groups/{group_id}/contacts",
                params=params
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_services":
            group_id = arguments["group_id"]
            
            result = await api_client.make_request(
                "GET",
                f"/groups/{group_id}/accounts/services"
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="comlaude-api",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
