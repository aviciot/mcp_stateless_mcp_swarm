"""
MCP Client Test Script
======================
Tests the MCP server using the official MCP Python client.
This simulates how a real MCP client (like Claude, Mastra, etc.) would connect.

Usage:
    python test_mcp_client.py
    python test_mcp_client.py --url http://localhost:8150/mcp
"""

import asyncio
import argparse
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test_mcp_server(url: str):
    """Test MCP server with official MCP client"""
    
    print("=" * 60)
    print(f"🔗 Connecting to MCP Server: {url}")
    print("=" * 60)
    
    try:
        # Connect using Streamable HTTP transport
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                
                # Initialize the connection
                print("\n📡 Initializing MCP session...")
                init_result = await session.initialize()
                print(f"   Server: {init_result.serverInfo.name}")
                print(f"   Version: {init_result.serverInfo.version}")
                print(f"   Protocol: {init_result.protocolVersion}")
                
                # List available tools
                print("\n🔧 Listing available tools...")
                tools_result = await session.list_tools()
                print(f"   Found {len(tools_result.tools)} tool(s):")
                for tool in tools_result.tools:
                    print(f"   - {tool.name}: {tool.description[:50]}...")
                
                # Test echo tool
                print("\n🧪 Testing 'echo' tool...")
                
                # Test 1: Simple message
                print("\n   Test 1: Simple echo")
                result = await session.call_tool("echo", {"message": "Hello from MCP Client!"})
                print(f"   Response: {result.content[0].text if result.content else 'No content'}")
                
                # Test 2: Repeat message
                print("\n   Test 2: Echo with repeat=3")
                result = await session.call_tool("echo", {"message": "Hi Avi", "repeat": 3})
                print(f"   Response:\n{result.content[0].text if result.content else 'No content'}")
                
                # Test 3: Edge case - repeat=10 (max)
                print("\n   Test 3: Echo with repeat=10 (max)")
                result = await session.call_tool("echo", {"message": "🚀", "repeat": 10})
                print(f"   Response: {result.content[0].text if result.content else 'No content'}")
                
                # Test 4: Error case - repeat > 10
                print("\n   Test 4: Echo with repeat=15 (should error)")
                result = await session.call_tool("echo", {"message": "test", "repeat": 15})
                print(f"   Response: {result.content[0].text if result.content else 'No content'}")
                
                # List resources (if any)
                print("\n📁 Listing resources...")
                try:
                    resources_result = await session.list_resources()
                    print(f"   Found {len(resources_result.resources)} resource(s)")
                    for resource in resources_result.resources:
                        print(f"   - {resource.uri}: {resource.name}")
                except Exception as e:
                    print(f"   No resources or error: {e}")
                
                # List prompts (if any)
                print("\n💬 Listing prompts...")
                try:
                    prompts_result = await session.list_prompts()
                    print(f"   Found {len(prompts_result.prompts)} prompt(s)")
                    for prompt in prompts_result.prompts:
                        print(f"   - {prompt.name}: {prompt.description}")
                except Exception as e:
                    print(f"   No prompts or error: {e}")
                
                print("\n" + "=" * 60)
                print("✅ All tests completed successfully!")
                print("=" * 60)
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


async def test_multiple_requests(url: str, count: int = 10):
    """Test multiple rapid requests to verify stateless mode works"""
    
    print("\n" + "=" * 60)
    print(f"🔄 Testing {count} rapid requests (stateless mode verification)")
    print("=" * 60)
    
    success = 0
    failed = 0
    
    for i in range(count):
        try:
            async with streamablehttp_client(url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool("echo", {"message": f"Request {i+1}"})
                    if result.content:
                        success += 1
                        print(f"   Request {i+1}: ✅")
                    else:
                        failed += 1
                        print(f"   Request {i+1}: ❌ No content")
        except Exception as e:
            failed += 1
            print(f"   Request {i+1}: ❌ {e}")
    
    print(f"\n📊 Results: {success}/{count} successful, {failed}/{count} failed")
    return success == count


def main():
    parser = argparse.ArgumentParser(description="Test MCP Server with official MCP client")
    parser.add_argument("--url", default="http://localhost:8150/mcp", help="MCP server URL")
    parser.add_argument("--rapid", type=int, default=0, help="Number of rapid requests to test")
    args = parser.parse_args()
    
    # Run main tests
    asyncio.run(test_mcp_server(args.url))
    
    # Run rapid request tests if requested
    if args.rapid > 0:
        asyncio.run(test_multiple_requests(args.url, args.rapid))


if __name__ == "__main__":
    main()
