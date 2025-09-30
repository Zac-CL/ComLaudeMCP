#!/usr/bin/env python3
"""
MCP Server for Com Laude API
Provides access to Com Laude's domain management, SSL, and account services
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin, urlparse

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
    ReadResourceRequest,
    Resource,
    ResourceContents,
    TextContent,
    Tool,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIConfigurationError(RuntimeError):
    """Raised when the API client is not properly configured."""


@dataclass
class APIConfigSnapshot:
    base_url: str
    api_key: str


class APISettingsManager:
    """Manage shared API configuration with async safety."""

    def __init__(self, base_url: str, api_key: Optional[str] = None) -> None:
        self._base_url = base_url
        self._api_key = api_key.strip() if api_key else None
        self._lock = asyncio.Lock()

    async def update(self, *, api_key: str, base_url: Optional[str] = None) -> None:
        cleaned_key = api_key.strip()
        if not cleaned_key:
            raise APIConfigurationError("API key cannot be empty. Provide a valid Com Laude API key.")

        async with self._lock:
            self._api_key = cleaned_key
            if base_url:
                cleaned_url = base_url.strip()
                if cleaned_url:
                    parsed_url = urlparse(cleaned_url)
                    if not all([parsed_url.scheme, parsed_url.netloc]):
                        raise APIConfigurationError(f"Invalid base_url: {base_url}")
                    self._base_url = cleaned_url

    async def snapshot(self) -> APIConfigSnapshot:
        async with self._lock:
            if not self._api_key:
                raise APIConfigurationError(
                    "API key is not configured. Set the COMLAUDE_API_KEY environment variable or use the configure_api tool to set it."
                )
            return APIConfigSnapshot(base_url=self._base_url, api_key=self._api_key)

class ComLaudeAPIClient:
    """Client for Com Laude API operations."""

    def __init__(
        self,
        settings: APISettingsManager,
        *,
        default_timeout: float = 30.0,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
    ) -> None:
        self._settings = settings
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    def update_defaults(
        self,
        *,
        default_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
    ) -> None:
        if default_timeout is not None:
            if default_timeout <= 0:
                raise ValueError("Default timeout must be greater than zero seconds.")
            self._default_timeout = default_timeout

        if max_retries is not None:
            if max_retries < 0:
                raise ValueError("Max retries cannot be negative.")
            self._max_retries = max_retries

        if backoff_factor is not None:
            if backoff_factor < 0:
                raise ValueError("Backoff factor cannot be negative.")
            self._backoff_factor = backoff_factor

    def get_defaults(self) -> Dict[str, Any]:
        return {
            "timeout": self._default_timeout,
            "max_retries": self._max_retries,
            "backoff_factor": self._backoff_factor,
        }

    async def make_request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Make HTTP request to Com Laude API with validation and retries."""

        config = await self._settings.snapshot()
        url = urljoin(config.base_url, endpoint)

        client_timeout = timeout if timeout is not None else self._default_timeout
        if client_timeout <= 0:
            raise ValueError("Timeout must be greater than zero seconds.")

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        attempt = 0
        last_error: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=client_timeout) as client:
            while attempt <= self._max_retries:
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=data,
                    )
                    response.raise_for_status()
                    if response.headers.get("Content-Type", "").startswith("application/json"):
                        return response.json()
                    return response.text
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status == 401:
                        logger.error("Received 401 Unauthorized from Com Laude API. Verify API key.")
                        raise APIConfigurationError("Unauthorized: check API key permissions and validity.") from exc

                    if status == 429 and attempt < self._max_retries:
                        backoff_seconds = self._backoff_factor * (2 ** attempt)
                        logger.warning(
                            "Received 429 Too Many Requests. Retrying in %.2f seconds (attempt %d/%d).",
                            backoff_seconds,
                            attempt + 1,
                            self._max_retries,
                        )
                        await asyncio.sleep(backoff_seconds)
                        attempt += 1
                        continue

                    masked_body = "<omitted>" if exc.response.content else ""
                    logger.error(
                        "HTTP error %s from Com Laude API: %s", status, masked_body
                    )
                    raise
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt < self._max_retries:
                        backoff_seconds = self._backoff_factor * (2 ** attempt)
                        logger.warning(
                            "Request error: %s. Retrying in %.2f seconds (attempt %d/%d).",
                            exc,
                            backoff_seconds,
                            attempt + 1,
                            self._max_retries,
                        )
                        await asyncio.sleep(backoff_seconds)
                        attempt += 1
                        continue
                    logger.error("Request error after retries: %s", exc)
                    raise

        if last_error:
            raise last_error

        raise RuntimeError("Unexpected request failure without captured exception.")


default_settings = APISettingsManager(
    base_url=os.getenv("COMLAUDE_BASE_URL", "https://api.comlaude.com"),
    api_key=os.getenv("COMLAUDE_API_KEY"),
)

api_client = ComLaudeAPIClient(default_settings)

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


RESOURCE_CONTENT_TEMPLATES: Dict[str, str] = {
    "comlaude://accounts": (
        "Use tools like get_accounts, get_account, update_account, and search_accounts to "
        "retrieve and manage account information."
    ),
    "comlaude://domains": (
        "Use get_domains and get_domain tools to inspect domain registrations and DNS details."
    ),
    "comlaude://ssl-certificates": (
        "Use get_ssl_certificates to list certificates with pagination support."
    ),
    "comlaude://contacts": (
        "Use get_contacts to list and page through contact information."
    ),
    "comlaude://services": (
        "Use get_services to view available services for a group."
    ),
}


@server.read_resource()
async def handle_read_resource(request: ReadResourceRequest) -> ResourceContents:
    """Provide guidance for static resources."""
    description = RESOURCE_CONTENT_TEMPLATES.get(request.uri)
    if not description:
        raise ValueError(f"Unknown resource URI: {request.uri}")

    return ResourceContents(contents=[
        TextContent(type="text", text=description)
    ])

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
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Default request timeout in seconds"
                    },
                    "max_retries": {
                        "type": "integer",
                        "description": "Maximum retry attempts for transient errors",
                        "default": 5
                    },
                    "backoff_factor": {
                        "type": "number",
                        "description": "Backoff factor (seconds) for retry delays",
                        "default": 1.0
                    }
                },
                "required": ["api_key"]
            }
        )
    ]

def _create_error_response(message: str, error_type: str = "error") -> List[TextContent]:
    """Create a structured JSON error response."""
    return [TextContent(
        type="text",
        text=json.dumps({"error": {"type": error_type, "message": message}}, indent=2)
    )]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "configure_api":
            api_key = arguments.get("api_key")
            base_url = arguments.get("base_url")
            if api_key is None:
                raise APIConfigurationError("api_key is required for configure_api")

            if base_url:
                await default_settings.update(api_key=api_key, base_url=base_url)
            else:
                await default_settings.update(api_key=api_key)

            timeout = arguments.get("timeout")
            max_retries = arguments.get("max_retries")
            backoff_factor = arguments.get("backoff_factor")

            api_client.update_defaults(
                default_timeout=timeout,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
            )

            snapshot = await default_settings.snapshot()
            defaults = api_client.get_defaults()
            return [TextContent(
                type="text",
                text=(
                    "API client configured. "
                    f"Base URL: {snapshot.base_url}. Timeout={defaults['timeout']}s, "
                    f"max_retries={defaults['max_retries']}, "
                    f"backoff_factor={defaults['backoff_factor']}"
                )
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
            page = arguments.get("page", 1)
            
            params = {
                "limit": limit,
                "page": page
            }
            
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
            return _create_error_response(f"Unknown tool: {name}", error_type="unknown_tool")
    except APIConfigurationError as e:
        logger.error(f"API Configuration Error calling tool {name}: {e}")
        return _create_error_response(str(e), error_type="configuration_error")
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return _create_error_response(f"An unexpected error occurred: {str(e)}")

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
