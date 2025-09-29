#!/usr/bin/env python3
"""
Simple test script to verify the MCP server setup
"""

import asyncio
import sys
import json

def test_imports():
    """Test that all required imports work"""
    try:
        import httpx
        print("✓ httpx imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import httpx: {e}")
        return False
    
    try:
        from mcp.server import Server
        print("✓ MCP server imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import MCP server: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic server functionality"""
    try:
        from mcp_server import ComLaudeAPIClient
        
        # Test client initialization
        client = ComLaudeAPIClient("https://api.comlaude.com", "test_key")
        print("✓ ComLaudeAPIClient initialized successfully")
        
        # Test headers
        expected_auth = "Bearer test_key"
        if client.headers.get("Authorization") == expected_auth:
            print("✓ Authorization header set correctly")
        else:
            print("✗ Authorization header not set correctly")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Failed basic functionality test: {e}")
        return False

async def test_async_functionality():
    """Test async functionality"""
    try:
        from mcp_server import ComLaudeAPIClient
        
        client = ComLaudeAPIClient("https://httpbin.org", "test_key")
        
        # Test a simple request (using httpbin.org for testing)
        try:
            result = await client.make_request("GET", "/get")
            print("✓ Async HTTP request successful")
            return True
        except Exception as e:
            print(f"✗ Async HTTP request failed: {e}")
            return False
    except Exception as e:
        print(f"✗ Failed async functionality test: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Com Laude MCP Server Setup")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Please install dependencies:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality tests failed")
        sys.exit(1)
    
    # Test async functionality
    try:
        result = asyncio.run(test_async_functionality())
        if not result:
            print("\n❌ Async functionality tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Async test error: {e}")
        sys.exit(1)
    
    print("\n✅ All tests passed! The MCP server is ready to use.")
    print("\nNext steps:")
    print("1. Set your API key in the environment or .env file")
    print("2. Run: docker-compose up --build")
    print("3. Or run locally: python mcp_server.py")

if __name__ == "__main__":
    main()

