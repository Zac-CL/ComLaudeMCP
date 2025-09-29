#!/bin/bash

# Com Laude MCP Server Startup Script

set -e

echo "🚀 Starting Com Laude MCP Server"
echo "================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from example..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "📝 Created .env file from env.example"
        echo "🔧 Please edit .env and add your API key before running again"
        exit 1
    else
        echo "❌ No env.example file found. Please create .env manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose."
    exit 1
fi

# Build and start the container
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting container..."
docker-compose up -d

echo "📊 Checking container status..."
sleep 2
docker-compose ps

echo ""
echo "✅ Com Laude MCP Server is starting up!"
echo ""
echo "📋 Useful commands:"
echo "  View logs:     docker-compose logs -f comlaude-mcp-server"
echo "  Stop server:   docker-compose down"
echo "  Restart:       docker-compose restart comlaude-mcp-server"
echo "  Health check:  docker-compose ps"
echo ""
echo "🔗 The server is now available for MCP connections."

